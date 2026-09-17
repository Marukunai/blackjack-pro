# engine/game_engine.py
# GameEngine: orquestador principal del flujo de partida.
# Máquina de estados que conecta core ↔ engine ↔ ui.
#
# Soporta 1-3 jugadores humanos en la misma mesa (multijugador local, "pasa
# y juega"): cada jugador tiene su propio Player (fichas, manos) y su propio
# StatisticsManager (perfil local, historial, logros), pero comparten un
# único crupier y un único zapato. Dentro de una ronda, el "foco" de la
# mesa (apuesta → reparto → seguro → turno de juego) pasa de un jugador al
# siguiente en orden de asiento — ver active_player_index y el evento
# on_turn_change, que la UI usa para saber a quién mostrar en cada momento.
# -------------------------------------------------------------
from __future__ import annotations

from typing import Callable, Optional

from config import i18n
from core.card import Card
from core.deck import Deck
from core.dealer import Dealer
from core.player import Player
from core.rules import Rules
from engine.actions import (
    available_actions, action_hit, action_stand,
    action_double, action_split, action_surrender,
    action_even_money,
)
from engine.game_state import GameState, ActionResult, RoundResult
from engine.payout import apply_payouts, HandPayout
from engine.side_bets import evaluate_perfect_pairs, evaluate_21_plus_3, SideBetOutcome
from engine.statistics import StatisticsManager


class GameEngine:
    """
    Orquesta el ciclo completo de una partida de Blackjack, con 1 a 3
    jugadores humanos compartiendo mesa y crupier.

    La UI llama a los métodos públicos (start_round, player_action, …)
    y escucha los callbacks de evento para actualizar la pantalla.

    Callbacks disponibles (todos opcionales):
        on_state_change(new_state: GameState)
        on_turn_change(player_index: int, phase: str)
            El foco de la mesa pasa a `player_index` (0-based, orden de
            asiento) en la fase `phase`: "bet" | "deal" | "insurance" | "play".
        on_card_dealt(card: Card, target: str, hand_index: int, player_index: Optional[int])
            target='dealer' → player_index es None.
            target='player' → player_index identifica al jugador (0-based).
        on_action_result(result: ActionResult)
        on_round_end(payouts: list[HandPayout])
            Lista PLANA de pagos de todos los jugadores (compatibilidad con
            el modo un jugador / consola).
        on_round_end_players(payouts_by_player: list[list[HandPayout]])
            Lista de listas, una por jugador (en orden de asiento) — la usa
            la UI multijugador para mostrar el resultado de cada uno.
        on_message(msg: str)
        on_achievements_unlocked(player_index: int, achievements: list)
        on_side_bets_result(player_index: int, outcomes: list[SideBetOutcome])
            Se emite justo tras repartir las 2 cartas iniciales de
            `player_index` (antes incluso de preguntar por el seguro), solo
            si tenía alguna apuesta lateral colocada.
    """

    def __init__(
        self,
        rules: Optional[Rules] = None,
        players: Optional[list[dict]] = None,
        player_name: str = "Player",
        profile_id: Optional[int] = None,
        preset_name: str = "",
    ) -> None:
        self.rules = rules or Rules()

        # `players`: lista de dicts {"name":..., "profile_id":...}, uno por
        # asiento (1-3). Si no se indica, se arma un único asiento con los
        # parámetros sueltos de siempre — así el modo consola y cualquier
        # llamada antigua de un solo jugador siguen funcionando sin cambios.
        if not players:
            players = [{"name": player_name, "profile_id": profile_id}]

        self.players: list[Player] = [
            Player(name=p.get("name", "Jugador"), chips=self.rules.starting_chips)
            for p in players
        ]
        self.stats_mgrs: list[StatisticsManager] = [
            StatisticsManager(self.players[i], profile_id=players[i].get("profile_id"))
            for i in range(len(players))
        ]
        for mgr in self.stats_mgrs:
            mgr.preset_name = preset_name

        # Con más de un jugador, quien se queda sin fichas recarga al saldo
        # inicial en su siguiente turno de apuesta (es una partida local
        # entre amigos: nadie se queda fuera de la mesa para siempre por
        # una mala racha). En solitario se mantiene el comportamiento
        # histórico: solo se repone UNA VEZ al cargar la partida — si te
        # quedas sin fichas a media sesión, la partida termina de verdad.
        self._multiplayer: bool = len(self.players) > 1

        self.dealer = Dealer()
        self.deck   = Deck(
            num_decks=self.rules.num_decks,
            penetration=self.rules.penetration,
        )

        self.state: GameState = GameState.MENU
        self.active_player_index: int = 0
        self._insurance_offered: bool = False
        self._round_payouts: list[HandPayout] = []
        self._round_payouts_by_player: list[list[HandPayout]] = []

        # Índice interno del reparto en curso (uno por jugador, en orden).
        self._deal_index: int = -1

        # Si es False, el turno del crupier NO se resuelve de golpe al
        # terminar el turno del jugador: la UI (Renderer) debe pedir cartas
        # una a una con `dealer_needs_card()` / `dealer_deal_next_card()` y
        # cerrar la ronda con `finish_dealer_turn()`, para poder animar cada
        # paso. El modo consola deja esto en True (comportamiento síncrono
        # de siempre).
        self.auto_dealer_turn: bool = True

        # Igual que auto_dealer_turn, pero para el reparto inicial: con
        # varios jugadores hay que animar el reparto de CADA uno por
        # separado antes de pasar al siguiente. Si es False, cada llamada
        # interna reparte solo al jugador que toca y se detiene; la UI debe
        # llamar a `continue_round()` cuando esté lista para el siguiente
        # paso (cartas ya aterrizadas). El modo consola lo deja en True.
        self.auto_advance: bool = True

        # Callbacks registrados por la UI
        self._callbacks: dict[str, list[Callable]] = {
            "on_state_change": [],
            "on_turn_change": [],
            "on_card_dealt": [],
            "on_action_result": [],
            "on_round_end": [],
            "on_round_end_players": [],
            "on_message": [],
            "on_achievements_unlocked": [],
            "on_side_bets_result": [],
        }

    # ------------------------------------------------------------------
    # Jugador / estadísticas "activos" (a quien le toca en este momento)
    # ------------------------------------------------------------------
    @property
    def player(self) -> Player:
        """El jugador con el foco de la mesa ahora mismo (apostando,
        recibiendo cartas, o jugando su turno). En modo un jugador es
        siempre el único jugador, como siempre."""
        return self.players[self.active_player_index]

    @property
    def stats_mgr(self) -> StatisticsManager:
        return self.stats_mgrs[self.active_player_index]

    # ------------------------------------------------------------------
    # Registro de callbacks
    # ------------------------------------------------------------------
    def on(self, event: str, fn: Callable) -> None:
        if event in self._callbacks:
            self._callbacks[event].append(fn)

    def _emit(self, event: str, *args) -> None:
        for fn in self._callbacks.get(event, []):
            fn(*args)

    # ------------------------------------------------------------------
    # API pública — flujo principal
    # ------------------------------------------------------------------
    def start_game(self) -> None:
        """Carga el perfil guardado de cada jugador y empieza la ronda de
        apuestas.

        Si el saldo guardado de alguien no llega ni a la apuesta mínima
        (partida anterior terminada en bancarrota), no tiene sentido
        cargarlo tal cual: dejaría la partida bloqueada para siempre sin
        forma de volver a jugar. En ese caso se repone el saldo inicial del
        preset actual, como un "perfil nuevo" — igual que ha funcionado
        siempre en modo un jugador.
        """
        for mgr in self.stats_mgrs:
            mgr.load()
        for p in self.players:
            if p.chips < self.rules.min_bet:
                p.chips = self.rules.starting_chips
        self._begin_betting_round()

    def place_bet(self, amount: float, perfect_pairs: float = 0.0,
                  twentyone_plus_three: float = 0.0) -> bool:
        """
        El jugador con el foco coloca su apuesta principal y, opcionalmente,
        sus apuestas laterales (Parejas Perfectas / 21+3 — ignoradas si la
        cantidad es 0 o si la regla correspondiente no está activa).
        Devuelve True si es válida; en ese caso pasa el foco al siguiente
        jugador pendiente de apostar, o reparte si ya han apostado todos.
        """
        if self.state != GameState.BETTING:
            return False
        if not (self.rules.min_bet <= amount <= self.rules.max_bet):
            self._emit("on_message", i18n.t("engine.invalid_bet", min=self.rules.min_bet, max=self.rules.max_bet))
            return False

        if not self.rules.perfect_pairs_allowed:
            perfect_pairs = 0.0
        if not self.rules.twentyone_plus_three_allowed:
            twentyone_plus_three = 0.0
        for side_amount in (perfect_pairs, twentyone_plus_three):
            if side_amount and not (0 < side_amount <= self.rules.side_bet_max):
                self._emit("on_message", i18n.t("engine.invalid_side_bet", max=self.rules.side_bet_max))
                return False

        total = amount + perfect_pairs + twentyone_plus_three
        if not self.player.can_afford(total):
            self._emit("on_message", i18n.t("engine.not_enough_chips"))
            return False

        self.player.place_bet(amount)
        self.player.new_round(amount)
        if perfect_pairs or twentyone_plus_three:
            self.player.place_side_bets(perfect_pairs, twentyone_plus_three)
        self._advance_to_next_bettor()
        return True

    def player_action(self, action: str) -> ActionResult:
        """
        Procesa una acción del jugador con el foco: 'hit','stand','double',
        'split','surrender'. Devuelve ActionResult.INVALID si la acción no
        está disponible.
        """
        if self.state != GameState.PLAYER_TURN:
            return ActionResult.INVALID

        hand = self.player.active_hand
        if hand is None or hand.is_finished:
            return ActionResult.INVALID

        is_first = len(hand.cards) == 2 and not hand.is_split
        valid = available_actions(hand, self.player, self.dealer, self.rules, is_first)

        if action not in valid:
            self._emit("on_message", i18n.t("engine.action_unavailable", action=action))
            return ActionResult.INVALID

        result = ActionResult.INVALID
        player = self.player

        match action:
            case "hit":
                result = action_hit(hand, self.deck)
                self._emit("on_card_dealt", hand.cards[-1], "player", player.active_hand_index, self.active_player_index)
            case "stand":
                result = action_stand(hand)
            case "double":
                result = action_double(hand, self.deck, player)
                self._emit("on_card_dealt", hand.cards[-1], "player", player.active_hand_index, self.active_player_index)
            case "split":
                hand1, hand2 = action_split(hand, self.deck, player, self.rules)
                # Reemplazar mano actual con las dos nuevas
                idx = player.active_hand_index
                player.hands[idx] = hand1
                player.hands.insert(idx + 1, hand2)
                result = ActionResult.SPLIT_DONE
                player.stats.hands_split += 1
                self._emit("on_card_dealt", hand1.cards[-1], "player", idx, self.active_player_index)
                self._emit("on_card_dealt", hand2.cards[-1], "player", idx + 1, self.active_player_index)
            case "surrender":
                result = action_surrender(hand, self.rules)

        # Tras la acción, si la mano activa ha quedado terminada (plantada,
        # pasada, rendida, 21, o —justo tras un split— la nueva mano activa
        # ya viene resuelta de antemano, como los Ases spliteados que
        # plantan automáticamente) se avanza a la siguiente mano de ESTE
        # jugador, encadenando el avance si esa también viniera terminada.
        # Si ya no le quedan más manos, el foco pasa al siguiente jugador
        # de la mesa (o al turno del crupier si no queda ninguno).
        #
        # IMPORTANTE: on_action_result se emite DESPUÉS de todo esto, no
        # antes — ver el comentario histórico más abajo, la razón sigue
        # aplicando igual con varios jugadores.
        active = player.active_hand
        while active is not None and active.is_finished:
            if not player.advance_hand():
                active = None
            else:
                active = player.active_hand

        if active is None:
            # Caso especial: doblar en multijugador (con la UI llevando el
            # ritmo a mano, auto_advance=False) termina la mano al instante
            # -- una única carta y a plantarse-- justo cuando acaba de
            # repartirse esa carta. Si se pasara el foco al siguiente
            # jugador en este mismo paso, la UI ni llegaría a mostrar la
            # carta recién llegada antes de que la mesa cambiara de sitio.
            # Se difiere el avance: el estado se queda en PLAYER_TURN con
            # la mano ya resuelta (get_available_actions() ya devuelve
            # [], así que no hay botones que pulsar) y es la propia UI
            # quien, tras pausar un par de segundos para que se vea bien
            # la carta, llama a continue_round() -- que retoma este mismo
            # camino más abajo y, con la mano ya en None, entra directo
            # por _advance_to_next_active_player().
            if action == "double" and self._multiplayer and not self.auto_advance:
                pass
            else:
                self._advance_to_next_active_player()

        self._emit("on_action_result", result)

        return result

    def accept_insurance(self, accept: bool) -> None:
        """El jugador con el foco decide sobre el seguro / even money."""
        if self.state != GameState.INSURANCE:
            return

        player = self.player
        if accept:
            hand = player.active_hand
            if hand and hand.is_blackjack and action_even_money(player, self.dealer, self.rules):
                # Even money: cobrar 1:1 inmediatamente y terminar la mano
                player.receive(hand.bet * 2)
                hand.stood = True
                self._emit("on_message", i18n.t("engine.even_money_paid", name=player.name))
            else:
                # Seguro estándar
                max_ins = player.active_hand.bet / 2 if player.active_hand else 0
                if player.can_afford(max_ins):
                    player.place_insurance(max_ins)

        if self.auto_advance:
            self._deal_next_player()
        else:
            # Vuelve a un estado "de reparto en pausa": la UI llama a
            # continue_round() cuando esté lista para seguir con el
            # siguiente jugador (o comprobar el BJ del crupier si era el
            # último).
            self._transition(GameState.DEALING)

    def continue_round(self) -> None:
        """Avanza un paso más cuando la UI ha terminado de mostrar el paso
        actual y espera una señal explícita para continuar:

        - En DEALING (reparto con `auto_advance=False`): reparte al
          siguiente jugador — ver `_deal_next_player()`.
        - En PLAYER_TURN: esto solo ocurre en multijugador, cuando el
          jugador con el foco no tenía ninguna acción posible de entrada
          (blackjack natural — ver `_advance_to_next_active_player()`). La
          UI ya le ha enseñado su mano un instante; toca pasar a la
          siguiente mano jugable de este jugador si le queda alguna
          (p. ej. tras un split ya resuelto) o, si no, al siguiente
          jugador de la mesa."""
        if self.state == GameState.DEALING:
            self._deal_next_player()
        elif self.state == GameState.PLAYER_TURN:
            hand = self.player.active_hand
            while hand is not None and hand.is_finished:
                if not self.player.advance_hand():
                    hand = None
                else:
                    hand = self.player.active_hand
            if hand is not None:
                self._transition(GameState.PLAYER_TURN)
                self._emit("on_turn_change", self.active_player_index, "play")
            else:
                self._advance_to_next_active_player()

    # ------------------------------------------------------------------
    # Flujo interno — apuestas
    # ------------------------------------------------------------------
    def _begin_betting_round(self) -> None:
        self._advance_to_next_bettor(from_start=True)

    def _advance_to_next_bettor(self, from_start: bool = False) -> None:
        n = len(self.players)
        i = 0 if from_start else self.active_player_index + 1
        if i >= n:
            self._deal_initial()
            return

        player = self.players[i]
        if player.chips < self.rules.min_bet:
            if self._multiplayer:
                player.chips = self.rules.starting_chips
            else:
                self._transition(GameState.GAME_OVER)
                self._emit("on_message", i18n.t("engine.out_of_chips"))
                return

        self.active_player_index = i
        self._transition(GameState.BETTING)
        self._emit("on_turn_change", i, "bet")

    # ------------------------------------------------------------------
    # Flujo interno — reparto inicial
    # ------------------------------------------------------------------
    def _deal_initial(self) -> None:
        """Reparte las dos cartas del crupier (una visible, una oculta) y
        empieza el reparto jugador a jugador."""
        self.dealer.reset()

        c = self.deck.deal()
        self.dealer.add_card(c)
        self._emit("on_card_dealt", c, "dealer", 0, None)

        c = self.deck.deal_hidden()
        self.dealer.add_card(c)
        self._emit("on_card_dealt", c, "dealer", 0, None)

        self._deal_index = -1
        # Al primer jugador se le reparte ya, en el mismo paso que al
        # crupier (sus cartas vuelan a la vez que las del crupier, tal
        # como se ha visto siempre en la mesa) — el "un jugador cada vez,
        # con pausa" de auto_advance=False solo hace falta para pasar el
        # foco de UN jugador a OTRO (ver _deal_next_player), no para
        # arrancar el reparto en sí.
        self._deal_next_player()

    def _deal_next_player(self) -> None:
        """Reparte 2 cartas al siguiente jugador pendiente y, si el crupier
        muestra un As y el seguro está permitido, se detiene a esperar su
        decisión. En modo auto_advance encadena automáticamente con el
        siguiente jugador (o con la comprobación de BJ del crupier al
        terminar); si no, se detiene tras cada jugador para que la UI anime
        su reparto antes de llamar a continue_round()."""
        n = len(self.players)
        self._deal_index += 1
        if self._deal_index >= n:
            self._finish_dealing()
            return

        i = self._deal_index
        self.active_player_index = i
        self._transition(GameState.DEALING)
        self._emit("on_turn_change", i, "deal")

        hand = self.players[i].active_hand
        c = self.deck.deal()
        hand.add_card(c)
        self._emit("on_card_dealt", c, "player", 0, i)
        c = self.deck.deal()
        hand.add_card(c)
        self._emit("on_card_dealt", c, "player", 0, i)

        self._resolve_side_bets(i, hand)

        if self.dealer.showing_ace and self.rules.insurance_allowed:
            self._transition(GameState.INSURANCE)
            self._emit("on_turn_change", i, "insurance")
            return   # espera a accept_insurance()

        if self.auto_advance:
            self._deal_next_player()
        # si no, se queda en DEALING hasta que la UI llame a continue_round()

    def _resolve_side_bets(self, player_index: int, hand) -> None:
        """Resuelve al instante las apuestas laterales de `player_index`
        (si tenía alguna colocada), usando ya la carta visible del crupier.
        Se paga/pierde de inmediato, sin esperar al resto de la ronda."""
        player = self.players[player_index]
        outcomes: list[SideBetOutcome] = []

        if player.perfect_pairs_bet > 0:
            bet = player.perfect_pairs_bet
            label, mult = evaluate_perfect_pairs(hand)
            if mult > 0:
                win = bet * mult
                player.receive(bet + win)
                outcomes.append(SideBetOutcome("perfect_pairs", label, mult, bet, win, bet + win))
            else:
                outcomes.append(SideBetOutcome("perfect_pairs", label, 0.0, bet, -bet, 0.0))

        if player.twentyone_plus_three_bet > 0:
            bet = player.twentyone_plus_three_bet
            label, mult = evaluate_21_plus_3(hand, self.dealer.upcard)
            if mult > 0:
                win = bet * mult
                player.receive(bet + win)
                outcomes.append(SideBetOutcome("21+3", label, mult, bet, win, bet + win))
            else:
                outcomes.append(SideBetOutcome("21+3", label, 0.0, bet, -bet, 0.0))

        if outcomes:
            self._emit("on_side_bets_result", player_index, outcomes)

    def _finish_dealing(self) -> None:
        """Ya se ha repartido (y decidido el seguro) a todos los
        jugadores: si el crupier tiene Blackjack la ronda se resuelve
        directamente; si no, empieza el turno de juego."""
        if self.dealer.has_blackjack:
            self.dealer.reveal_hole_card()
            self._emit("on_message", i18n.t("engine.dealer_has_blackjack"))
            self._end_round()
        else:
            self._begin_player_turns()

    # ------------------------------------------------------------------
    # Flujo interno — turno de los jugadores
    # ------------------------------------------------------------------
    def _begin_player_turns(self) -> None:
        self._advance_to_next_active_player(from_start=True)

    def _advance_to_next_active_player(self, from_start: bool = False) -> None:
        """Pasa el foco al siguiente jugador con una mano repartida.

        En solitario (y en consola) el comportamiento es el de siempre:
        si la única mano de ese jugador ya viene resuelta de entrada
        (Blackjack natural, even money…) se salta sin más, directo al
        turno del crupier — no hay nadie más en la mesa a quien
        enseñársela.

        En multijugador, en cambio, SIEMPRE se le da el foco un instante
        a cada jugador con una mano repartida, aunque ya venga resuelta y
        no tenga ninguna acción posible (Blackjack natural) — así se ve
        su mano en la mesa antes de pasar al siguiente, igual que haría
        un crupier real. La UI detecta que no hay acciones disponibles
        (`get_available_actions()` devuelve `[]`) y, tras una breve
        pausa, llama a `continue_round()` para seguir sola.

        Si nadie tiene ya nada por jugar, empieza el turno del crupier."""
        n = len(self.players)
        start = 0 if from_start else self.active_player_index + 1
        for i in range(start, n):
            p = self.players[i]
            active = p.active_hand
            if not self._multiplayer:
                while active is not None and active.is_finished:
                    if not p.advance_hand():
                        active = None
                    else:
                        active = p.active_hand
            if active is not None:
                self.active_player_index = i
                self._transition(GameState.PLAYER_TURN)
                self._emit("on_turn_change", i, "play")
                return

        if self.auto_dealer_turn:
            self._dealer_turn()
        else:
            self._begin_dealer_turn()

    # ------------------------------------------------------------------
    # Flujo interno — turno del crupier
    # ------------------------------------------------------------------
    def _dealer_turn(self) -> None:
        """El crupier revela la hole card y pide cartas según las reglas.

        Resuelve el turno completo de una vez (usado por el modo consola,
        donde no hay animaciones que esperar).
        """
        self._begin_dealer_turn()
        while self.dealer_needs_card():
            self.dealer_deal_next_card()
        self.finish_dealer_turn()

    # -- Versión paso a paso (usada por la UI Pygame para animar) --------
    def _begin_dealer_turn(self) -> None:
        """Inicia el turno del crupier: solo revela la hole card."""
        self._transition(GameState.DEALER_TURN)
        self.dealer.reveal_hole_card()

    def dealer_needs_card(self) -> bool:
        """True si el crupier debe pedir otra carta según las reglas."""
        if self.state != GameState.DEALER_TURN:
            return False
        return self.dealer.must_hit(self.rules)

    def dealer_deal_next_card(self) -> None:
        """Reparte una única carta al crupier (para pacing animado)."""
        if self.state != GameState.DEALER_TURN:
            return
        c = self.deck.deal()
        self.dealer.add_card(c)
        self._emit("on_card_dealt", c, "dealer", 0, None)

    def finish_dealer_turn(self) -> None:
        """Cierra el turno del crupier y resuelve la ronda."""
        if self.state != GameState.DEALER_TURN:
            return
        self._end_round()

    # ------------------------------------------------------------------
    # Flujo interno — resolución de la ronda
    # ------------------------------------------------------------------
    def _end_round(self) -> None:
        """Resuelve pagos para TODOS los jugadores, actualiza sus fichas y
        estadísticas (cada uno en su propio perfil local, si tiene uno) y
        prepara la siguiente ronda de apuestas."""
        self._transition(GameState.PAYOUT)

        payouts_by_player: list[list[HandPayout]] = []
        flat: list[HandPayout] = []

        for i, player in enumerate(self.players):
            payouts = apply_payouts(player, self.dealer, self.rules)
            payouts_by_player.append(payouts)
            flat.extend(payouts)

            mgr = self.stats_mgrs[i]
            mgr.log_round(payouts, dealer=self.dealer)
            mgr.save()

            # Logros: se comprueban tras guardar, para que usen las
            # estadísticas ya actualizadas con esta ronda. Solo tiene
            # sentido con un perfil local seleccionado.
            if mgr.profile_id is not None:
                from engine.achievements import check_and_unlock
                from engine.profile_store import get_store
                unlocked = check_and_unlock(player, mgr.profile_id, get_store())
                if unlocked:
                    self._emit("on_achievements_unlocked", i, unlocked)

        self._round_payouts = flat
        self._round_payouts_by_player = payouts_by_player
        self._emit("on_round_end", flat)
        self._emit("on_round_end_players", payouts_by_player)

        # ¿Rebarajar?
        if self.deck.penetration_reached:
            self.deck.shuffle()
            self._emit("on_message", i18n.t("engine.reshuffling"))

        self._begin_betting_round()

    def _transition(self, new_state: GameState) -> None:
        self.state = new_state
        self._emit("on_state_change", new_state)

    # ------------------------------------------------------------------
    # Consultas de estado para la UI
    # ------------------------------------------------------------------
    def get_available_actions(self) -> list[str]:
        hand = self.player.active_hand
        if hand is None or self.state != GameState.PLAYER_TURN:
            return []
        is_first = len(hand.cards) == 2 and not hand.is_split
        return available_actions(hand, self.player, self.dealer, self.rules, is_first)

    def get_round_summary(self) -> str:
        lines = []
        for i, p in enumerate(self._round_payouts):
            emoji = {"WIN": "✅", "BLACKJACK_WIN": "🌟", "LOSS": "❌",
                     "PUSH": "🤝", "SURRENDER": "🏳️", "DEALER_BUST": "💥"}.get(p.result.name, "")
            lines.append(f"  Mano {i+1}: {p.result.name} {emoji}  neto={p.net:+.0f}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        return (
            f"GameEngine(state={self.state.name}, "
            f"players={[str(p) for p in self.players]}, "
            f"deck={self.deck})"
        )
