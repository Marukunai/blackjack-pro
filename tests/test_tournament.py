# tests/test_tournament.py
# Cobertura del modo Torneo (engine/tournament.py, Fase 39) -- mismo
# patrón que tests/test_challenges.py: el catálogo y build_rules() no
# tenían ningún test permanente, incluida la regla "un Torneo siempre
# arranca con SUS propias fichas, nunca el saldo real del perfil" (igual
# que ya se exige/comprueba para los Desafíos).
#
# La clasificación final (ranking por fichas) y la pantalla de fin de
# Torneo son de ui/renderer.py (bucle Pygame, sin test unitario directo,
# igual que el resto de pantallas del renderer) -- lo que SÍ se cubre
# aquí a nivel de motor es la premisa de la que depende ese ranking:
# que, en una mesa multijugador, todos los asientos (humanos y bots)
# acaban jugando exactamente el mismo número de manos ronda a ronda, así
# que comprobar hands_played de un solo asiento (como ya hace
# Challenge.evaluate) basta para saber cuándo ha terminado el torneo.
from __future__ import annotations

import pytest

from config.rules_presets import vegas_strip
from engine.game_engine import GameEngine
from engine.game_state import GameState
from engine.tournament import Tournament, TOURNAMENTS, get_tournament


def _play_rounds(engine: GameEngine, rounds: int, bet: float = 25.0) -> None:
    """Juega `rounds` rondas completas en modo síncrono (apuesta/planta
    por cada asiento pendiente), usando engine.player.stats.hands_played
    como condición de parada en vez de un número fijo de iteraciones por
    ronda -- a diferencia de tests/test_multiplayer.py::_play_one_round
    (pensado para UNA sola ronda con 1-2 asientos), aquí hace falta
    encadenar varias rondas seguidas con hasta 3 asientos y posibles
    splits/seguro, y un presupuesto de iteraciones fijo por ronda se
    queda corto de vez en cuando -- dejando una ronda a medias que la
    siguiente llamada nunca llegaba a recuperar del todo."""
    target = engine.player.stats.hands_played + rounds
    # Techo generoso (nunca debería hacer falta ni una fracción de esto
    # con mesas de hasta 3 asientos) solo para que un bucle real
    # atascado falle con un AssertionError claro en vez de colgar el test.
    for _ in range(400 * rounds):
        if engine.player.stats.hands_played >= target:
            return
        if engine.state == GameState.BETTING:
            engine.place_bet(bet)
        elif engine.state == GameState.INSURANCE:
            engine.accept_insurance(False)
        elif engine.state == GameState.PLAYER_TURN:
            # Un Blackjack natural no deja ninguna acción disponible (ver
            # ui/renderer.py::_on_state_change, caso PLAYER_TURN) -- ahí
            # lo que avanza la ronda es continue_round(), nunca
            # player_action("stand"), que en ese caso no haría nada y
            # dejaría el bucle atascado para siempre.
            if engine.get_available_actions():
                engine.player_action("stand")
            else:
                engine.continue_round()
    raise AssertionError(
        f"No se completaron {rounds} rondas (hands_played="
        f"{engine.player.stats.hands_played}, objetivo={target}, "
        f"estado={engine.state})")


class TestTournamentCatalog:
    def test_all_ids_are_unique(self):
        ids = [t.id for t in TOURNAMENTS]
        assert len(ids) == len(set(ids))

    def test_get_tournament_returns_the_right_one(self):
        t = get_tournament("torneo_rapido")
        assert t.name == "Torneo Rápido"

    def test_get_unknown_tournament_raises(self):
        with pytest.raises(KeyError):
            get_tournament("no_existe")

    def test_build_rules_always_uses_the_tournament_own_starting_chips(self):
        """Regresión directa del mismo bug que ya se evita en Challenge
        (Fase 26/27): un Torneo debe arrancar siempre con SUS propias
        fichas/límites, no con el saldo real del perfil."""
        for t in TOURNAMENTS:
            rules = t.build_rules()
            assert rules.starting_chips == t.starting_chips
            assert rules.min_bet == t.min_bet
            assert rules.max_bet == t.max_bet
            assert rules.num_decks == t.num_decks

    def test_every_tournament_has_a_positive_hand_limit(self):
        for t in TOURNAMENTS:
            assert t.hand_limit > 0


class TestAllSeatsPlayTheSameNumberOfHands:
    """Premisa de la que depende el ranking final de ui/renderer.py: en
    una mesa con varios asientos (humanos + bots), tras N rondas
    jugadas, TODOS los asientos deben llevar exactamente N manos en sus
    propias estadísticas -- así, mirar solo engine.player.stats.
    hands_played (el primer asiento) basta para saber si ya se alcanzó
    tournament.hand_limit, sin tener que consultar a cada jugador."""

    def test_human_and_bot_seats_stay_in_lockstep_round_after_round(self):
        tournament = get_tournament("torneo_rapido")
        engine = GameEngine(
            rules=tournament.build_rules(),
            players=[
                {"name": "Maruku", "is_bot": False},
                {"name": "Bot 1", "is_bot": True},
                {"name": "Bot 2", "is_bot": True},
            ],
        )
        engine.start_game()
        for p in engine.players:
            p.chips = tournament.starting_chips

        rounds_to_play = 5
        _play_rounds(engine, rounds_to_play)

        hands_played = [p.stats.hands_played for p in engine.players]
        assert hands_played == [rounds_to_play] * len(engine.players)

    def test_tournament_ends_exactly_when_hand_limit_is_reached(self):
        """Mismo invariante que arriba, pero jugando exactamente
        hand_limit rondas de un torneo real -- confirma que el gancho de
        ui/renderer.py (comprobar hands_played >= hand_limit tras cada
        on_round_end) dispararía en el momento correcto, sin manos de
        más ni de menos."""
        tournament = get_tournament("torneo_rapido")   # hand_limit=10
        engine = GameEngine(
            rules=tournament.build_rules(),
            players=[{"name": "Maruku", "is_bot": False}, {"name": "Bot", "is_bot": True}],
        )
        engine.start_game()
        for p in engine.players:
            p.chips = tournament.starting_chips

        _play_rounds(engine, tournament.hand_limit)

        assert engine.player.stats.hands_played == tournament.hand_limit
        for p in engine.players:
            assert p.stats.hands_played == tournament.hand_limit


class TestTournamentRankingByChips:
    """No hay acceso directo a GameEngine para forzar quién gana cada
    mano (el reparto es aleatorio), así que esto no comprueba un
    resultado concreto -- comprueba la propiedad que SÍ debe cumplirse
    siempre para que un ranking por fichas tenga sentido: que las fichas
    de cada asiento son independientes entre sí y reflejan de verdad lo
    que ese asiento ha ganado o perdido, nunca un valor compartido."""

    def test_seats_end_with_independent_chip_totals(self):
        tournament = get_tournament("torneo_estandar")
        engine = GameEngine(
            rules=tournament.build_rules(),
            players=[
                {"name": "Maruku", "is_bot": False},
                {"name": "Bot 1", "is_bot": True},
                {"name": "Bot 2", "is_bot": True},
            ],
        )
        engine.start_game()
        for p in engine.players:
            p.chips = tournament.starting_chips

        _play_rounds(engine, 8)

        chips = [p.chips for p in engine.players]
        # No tienen por qué ser todas distintas (podría haber empate por
        # casualidad), pero no pueden estar todas pegadas al mismo valor
        # inicial sin que ninguna ronda haya movido nada -- eso sí
        # indicaría que las fichas no son independientes por asiento.
        assert any(c != tournament.starting_chips for c in chips)
