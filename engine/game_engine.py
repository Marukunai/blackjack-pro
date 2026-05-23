# engine/game_engine.py
# GameEngine: orquestador principal del flujo de partida.
# Máquina de estados que conecta core ↔ engine ↔ ui.
# -------------------------------------------------------------
from __future__ import annotations

from typing import Callable, Optional

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
from engine.statistics import StatisticsManager


class GameEngine:
    """
    Orquesta el ciclo completo de una partida de Blackjack.

    La UI llama a los métodos públicos (start_round, player_action, …)
    y escucha los callbacks de evento para actualizar la pantalla.

    Callbacks disponibles (todos opcionales):
        on_state_change(new_state: GameState)
        on_card_dealt(card: Card, target: str, hand_index: int)
        on_action_result(result: ActionResult)
        on_round_end(payouts: list[HandPayout])
        on_message(msg: str)
    """

    def __init__(
        self,
        rules: Optional[Rules] = None,
        player_name: str = "Player",
    ) -> None:
        self.rules = rules or Rules()
        self.player = Player(name=player_name, chips=self.rules.starting_chips)
        self.dealer = Dealer()
        self.deck   = Deck(
            num_decks=self.rules.num_decks,
            penetration=self.rules.penetration,
        )
        self.stats_mgr = StatisticsManager(self.player)

        self.state: GameState = GameState.MENU
        self._current_bet: float = 0.0
        self._insurance_offered: bool = False
        self._round_payouts: list[HandPayout] = []

        # Callbacks registrados por la UI
        self._callbacks: dict[str, list[Callable]] = {
            "on_state_change": [],
            "on_card_dealt": [],
            "on_action_result": [],
            "on_round_end": [],
            "on_message": [],
        }

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
        """Carga el perfil guardado y pasa al estado BETTING."""
        self.stats_mgr.load()
        self._transition(GameState.BETTING)

    def place_bet(self, amount: float) -> bool:
        """
        El jugador coloca su apuesta.
        Devuelve True si es válida y se inicia el reparto.
        """
        if self.state != GameState.BETTING:
            return False
        if not (self.rules.min_bet <= amount <= self.rules.max_bet):
            self._emit("on_message", f"Apuesta inválida. Min={self.rules.min_bet}, Max={self.rules.max_bet}")
            return False
        if not self.player.can_afford(amount):
            self._emit("on_message", "No tienes suficientes fichas.")
            return False

        self._current_bet = amount
        self.player.place_bet(amount)
        self._deal_initial()
        return True

    def player_action(self, action: str) -> ActionResult:
        """
        Procesa una acción del jugador: 'hit','stand','double','split','surrender'.
        Devuelve ActionResult.INVALID si la acción no está disponible.
        """
        if self.state != GameState.PLAYER_TURN:
            return ActionResult.INVALID

        hand = self.player.active_hand
        if hand is None or hand.is_finished:
            return ActionResult.INVALID

        is_first = len(hand.cards) == 2 and not hand.is_split
        valid = available_actions(hand, self.player, self.dealer, self.rules, is_first)

        if action not in valid:
            self._emit("on_message", f"Acción '{action}' no disponible ahora.")
            return ActionResult.INVALID

        result = ActionResult.INVALID

        match action:
            case "hit":
                result = action_hit(hand, self.deck)
                self._emit("on_card_dealt", hand.cards[-1], "player", self.player.active_hand_index)
            case "stand":
                result = action_stand(hand)
            case "double":
                result = action_double(hand, self.deck, self.player)
                self._emit("on_card_dealt", hand.cards[-1], "player", self.player.active_hand_index)
            case "split":
                hand1, hand2 = action_split(hand, self.deck, self.player, self.rules)
                # Reemplazar mano actual con las dos nuevas
                idx = self.player.active_hand_index
                self.player.hands[idx] = hand1
                self.player.hands.insert(idx + 1, hand2)
                result = ActionResult.SPLIT_DONE
                self._emit("on_card_dealt", hand1.cards[-1], "player", idx)
                self._emit("on_card_dealt", hand2.cards[-1], "player", idx + 1)
            case "surrender":
                result = action_surrender(hand, self.rules)

        self._emit("on_action_result", result)

        # ¿Turno del jugador terminado?
        if result in (ActionResult.STAND, ActionResult.BUST,
                      ActionResult.SURRENDER, ActionResult.TWENTY_ONE):
            if not self.player.advance_hand():
                # No quedan más manos → turno del crupier
                self._dealer_turn()
            # Si hay más splits, la UI actualizará active_hand

        return result

    def accept_insurance(self, accept: bool) -> None:
        """El jugador decide sobre el seguro / even money."""
        if self.state != GameState.INSURANCE:
            return

        if accept:
            hand = self.player.active_hand
            if hand and hand.is_blackjack and action_even_money(self.player, self.dealer, self.rules):
                # Even money: cobrar 1:1 inmediatamente y terminar la mano
                self.player.receive(hand.bet * 2)
                hand.stood = True
                self._emit("on_message", "Even Money cobrado.")
                self._end_round()
                return
            else:
                # Seguro estándar
                max_ins = self.player.active_hand.bet / 2 if self.player.active_hand else 0
                if self.player.can_afford(max_ins):
                    self.player.place_insurance(max_ins)

        # Comprobar si el crupier tiene blackjack
        if self.dealer.has_blackjack:
            self.dealer.reveal_hole_card()
            self._emit("on_message", "¡El crupier tiene Blackjack!")
            self._end_round()
        else:
            self._emit("on_message", "El crupier no tiene Blackjack. Continúa el juego.")
            self._transition(GameState.PLAYER_TURN)

    # ------------------------------------------------------------------
    # Flujo interno
    # ------------------------------------------------------------------
    def _deal_initial(self) -> None:
        """Reparte las 4 cartas iniciales: J-D-J-D (jugador-dealer alternado)."""
        self._transition(GameState.DEALING)
        hand = self.player.new_round(self._current_bet)

        # Carta 1 al jugador
        c = self.deck.deal()
        hand.add_card(c)
        self._emit("on_card_dealt", c, "player", 0)

        # Carta 1 al crupier (boca arriba — upcard)
        c = self.deck.deal()
        self.dealer.reset()
        self.dealer.add_card(c)
        self._emit("on_card_dealt", c, "dealer", 0)

        # Carta 2 al jugador
        c = self.deck.deal()
        hand.add_card(c)
        self._emit("on_card_dealt", c, "player", 0)

        # Carta 2 al crupier (hole card — boca abajo)
        c = self.deck.deal_hidden()
        self.dealer.add_card(c)
        self._emit("on_card_dealt", c, "dealer", 0)

        # Comprobar si hay seguro/even money disponible
        if self.dealer.showing_ace and self.rules.insurance_allowed:
            self._transition(GameState.INSURANCE)
            return

        # Comprobar Blackjack inmediato
        if hand.is_blackjack:
            if self.dealer.has_blackjack:
                self.dealer.reveal_hole_card()
                self._end_round()
                return
            self._end_round()
            return

        self._transition(GameState.PLAYER_TURN)

    def _dealer_turn(self) -> None:
        """El crupier revela la hole card y pide cartas según las reglas."""
        self._transition(GameState.DEALER_TURN)
        self.dealer.reveal_hole_card()

        while self.dealer.must_hit(self.rules):
            c = self.deck.deal()
            self.dealer.add_card(c)
            self._emit("on_card_dealt", c, "dealer", 0)

        self._end_round()

    def _end_round(self) -> None:
        """Resuelve pagos, actualiza fichas y prepara la siguiente ronda."""
        self._transition(GameState.PAYOUT)
        self._round_payouts = apply_payouts(self.player, self.dealer, self.rules)
        self._emit("on_round_end", self._round_payouts)
        self.stats_mgr.save()

        # ¿El jugador se quedó sin fichas?
        if self.player.chips < self.rules.min_bet:
            self._transition(GameState.GAME_OVER)
            self._emit("on_message", "¡Te has quedado sin fichas! Partida terminada.")
            return

        # ¿Rebarajar?
        if self.deck.penetration_reached:
            self.deck.shuffle()
            self._emit("on_message", "🔀 Rebarajando el zapato…")

        self._transition(GameState.BETTING)

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
            f"player={self.player}, "
            f"deck={self.deck})"
        )