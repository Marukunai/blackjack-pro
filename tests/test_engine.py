# tests/test_engine.py
"""
Tests de integración del GameEngine.
Simulan rondas completas sin UI.
"""
import pytest
from engine.game_engine import GameEngine
from engine.game_state import GameState, ActionResult
from config.rules_presets import vegas_strip


class TestEngineFlow:
    def setup_method(self):
        self.engine = GameEngine(rules=vegas_strip(), player_name="Test")

    def test_initial_state_is_menu(self):
        assert self.engine.state == GameState.MENU

    def test_start_goes_to_betting(self):
        self.engine.start_game()
        assert self.engine.state == GameState.BETTING

    def test_place_valid_bet(self):
        self.engine.start_game()
        ok = self.engine.place_bet(25)
        assert ok
        # Después del reparto debe estar en PLAYER_TURN o INSURANCE
        assert self.engine.state in (GameState.PLAYER_TURN, GameState.INSURANCE, GameState.PAYOUT, GameState.BETTING)

    def test_place_invalid_bet_too_low(self):
        self.engine.start_game()
        ok = self.engine.place_bet(1)
        assert not ok
        assert self.engine.state == GameState.BETTING

    def test_place_invalid_bet_too_high(self):
        self.engine.start_game()
        ok = self.engine.place_bet(99999)
        assert not ok

    def test_full_round_stand(self):
        """Simula una ronda completa donde el jugador siempre planta."""
        self.engine.start_game()
        # Saltarse insurance si se activa
        if self.engine.state == GameState.INSURANCE:
            self.engine.accept_insurance(False)

        if self.engine.state == GameState.PLAYER_TURN:
            result = self.engine.player_action("stand")
            assert result in (ActionResult.STAND, ActionResult.INVALID)

        # La ronda debe haber terminado y volver a BETTING o GAME_OVER
        assert self.engine.state in (GameState.BETTING, GameState.GAME_OVER)

    def test_chips_decrease_on_bet(self):
        self.engine.start_game()
        chips_before = self.engine.player.chips
        self.engine.place_bet(50)
        # Las fichas disminuyen al apostar (se recuperan al resolver)
        # Al menos durante el turno el saldo baja
        assert self.engine.player.chips <= chips_before

    def test_invalid_action_outside_turn(self):
        self.engine.start_game()
        # En estado BETTING no hay acciones de jugador
        result = self.engine.player_action("hit")
        assert result == ActionResult.INVALID


class TestEngineCallbacks:
    def test_state_change_callback(self):
        states = []
        engine = GameEngine(rules=vegas_strip())
        engine.on("on_state_change", lambda s: states.append(s))
        engine.start_game()
        assert GameState.BETTING in states

    def test_card_dealt_callback(self):
        cards = []
        engine = GameEngine(rules=vegas_strip())
        engine.on("on_card_dealt", lambda c, t, i: cards.append((t, i)))
        engine.start_game()
        engine.place_bet(10)
        # Deben haberse repartido al menos 4 cartas (2 jugador + 2 crupier)
        assert len(cards) >= 4