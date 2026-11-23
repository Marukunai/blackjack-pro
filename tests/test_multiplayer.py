# tests/test_multiplayer.py
# El motor soporta hasta 3 asientos locales "hot-seat" (ver
# engine/game_engine.py); hasta esta fase solo se habia probado a mano
# durante sesiones de desarrollo, nunca con un test permanente.
from __future__ import annotations

from config.rules_presets import vegas_strip
from engine.game_engine import GameEngine
from engine.game_state import GameState


def _two_player_engine() -> GameEngine:
    return GameEngine(
        rules=vegas_strip(),
        players=[{"name": "Maruku"}, {"name": "Aymane"}],
    )


class TestMultiplayerSetup:
    def test_creates_one_player_object_per_seat(self):
        engine = _two_player_engine()
        assert len(engine.players) == 2
        assert [p.name for p in engine.players] == ["Maruku", "Aymane"]

    def test_both_seats_start_with_the_rules_starting_chips(self):
        engine = _two_player_engine()
        for p in engine.players:
            assert p.chips == engine.rules.starting_chips


class TestMultiplayerBetting:
    def test_first_bettor_is_seat_zero(self):
        engine = _two_player_engine()
        engine.start_game()
        assert engine.active_player_index == 0

    def test_betting_advances_to_the_next_seat(self):
        engine = _two_player_engine()
        engine.start_game()
        engine.place_bet(25.0)
        # Tras apostar el primer asiento, el foco pasa al segundo (o ya
        # se ha repartido si era el ultimo pendiente) -- en una mesa de
        # 2, debe tocarle al asiento 1.
        assert engine.active_player_index in (0, 1)

    def test_each_seat_keeps_its_own_chip_balance(self):
        engine = _two_player_engine()
        engine.start_game()
        engine.place_bet(25.0)
        # El asiento que ya aposto tiene menos fichas que el que aun no
        # ha apostado (o ya se le han devuelto tras resolverse la mano).
        assert engine.players[0].chips != engine.rules.starting_chips or \
            engine.state in (GameState.PLAYER_TURN, GameState.BETTING)


def _play_one_round(engine, bet: float = 25.0, max_iterations: int = 20) -> None:
    """Juega una ronda completa en modo síncrono (auto_advance=True por
    defecto, como el modo consola): apuesta/planta por cada asiento
    pendiente hasta que la ronda se resuelve sola. Usado por los tests
    que necesitan estadísticas reales tras una ronda, sin depender de la
    animación/pacing de la UI Pygame."""
    for _ in range(max_iterations):
        if engine.state == GameState.BETTING:
            engine.place_bet(bet)
        elif engine.state == GameState.INSURANCE:
            engine.accept_insurance(False)
        elif engine.state == GameState.PLAYER_TURN:
            engine.player_action("stand")
        else:
            break


class TestBotTableAchievementTracking:
    """Fase 37: GameEngine._end_round() debe anotar en SessionStats
    cuántas manos ha jugado cada jugador en una mesa con algún asiento de
    IA -- alimenta el logro "Contra las máquinas". El motor en sí no
    distingue el comportamiento de un bot (eso lo hace ui/renderer.py),
    pero sí debe saber que `is_bot` estaba marcado en algún asiento."""

    def test_hands_vs_bot_increments_when_a_bot_sits_at_the_table(self):
        engine = GameEngine(
            rules=vegas_strip(),
            players=[{"name": "Maruku", "is_bot": False}, {"name": "Bot", "is_bot": True}],
        )
        engine.start_game()
        assert engine.players[0].stats.hands_vs_bot == 0
        _play_one_round(engine)
        assert engine.players[0].stats.hands_vs_bot >= 1
        assert engine.players[1].stats.hands_vs_bot >= 1

    def test_hands_vs_bot_stays_zero_without_any_bot(self):
        engine = _two_player_engine()
        engine.start_game()
        _play_one_round(engine)
        assert engine.players[0].stats.hands_vs_bot == 0
        assert engine.players[1].stats.hands_vs_bot == 0

    def test_solo_table_never_counts_as_vs_bot(self):
        engine = GameEngine(rules=vegas_strip(), player_name="Test")
        engine.start_game()
        _play_one_round(engine)
        assert engine.players[0].stats.hands_vs_bot == 0
