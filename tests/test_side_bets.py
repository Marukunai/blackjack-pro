# tests/test_side_bets.py
# Cobertura de engine/side_bets.py: Parejas Perfectas, 21+3, Lucky Ladies
# y Royal Match (Fase 31) -- antes de esta fase ninguna apuesta lateral
# tenia tests permanentes en el repo, solo verificacion manual puntual.
from __future__ import annotations

from core.card import Card
from core.hand import Hand
from engine.side_bets import (
    evaluate_perfect_pairs,
    evaluate_21_plus_3,
    evaluate_lucky_ladies,
    evaluate_royal_match,
    PERFECT_PAIRS_PAYOUTS,
    TWENTYONE_PLUS_THREE_PAYOUTS,
    LUCKY_LADIES_PAYOUTS,
    ROYAL_MATCH_PAYOUTS,
    SideBetOutcome,
)


def _hand(*cards: Card) -> Hand:
    h = Hand()
    for c in cards:
        h.add_card(c)
    return h


class TestPerfectPairs:
    def test_same_rank_same_suit_is_perfect_pair(self):
        label, mult = evaluate_perfect_pairs(_hand(Card("8", "♠"), Card("8", "♠")))
        assert label == "Pareja perfecta"
        assert mult == PERFECT_PAIRS_PAYOUTS["Pareja perfecta"]

    def test_same_rank_same_color_different_suit_is_colored_pair(self):
        label, mult = evaluate_perfect_pairs(_hand(Card("8", "♥"), Card("8", "♦")))
        assert label == "Pareja de color"
        assert mult == PERFECT_PAIRS_PAYOUTS["Pareja de color"]

    def test_same_rank_different_color_is_mixed_pair(self):
        label, mult = evaluate_perfect_pairs(_hand(Card("8", "♥"), Card("8", "♠")))
        assert label == "Pareja mixta"
        assert mult == PERFECT_PAIRS_PAYOUTS["Pareja mixta"]

    def test_no_pair_pays_nothing(self):
        label, mult = evaluate_perfect_pairs(_hand(Card("8", "♥"), Card("9", "♠")))
        assert label == "Sin pareja"
        assert mult == 0.0

    def test_incomplete_hand_pays_nothing(self):
        label, mult = evaluate_perfect_pairs(_hand(Card("8", "♥")))
        assert mult == 0.0


class Test21Plus3:
    def test_suited_trips(self):
        label, mult = evaluate_21_plus_3(_hand(Card("K", "♠"), Card("K", "♠")), Card("K", "♠"))
        assert label == "Trío de color"
        assert mult == TWENTYONE_PLUS_THREE_PAYOUTS["Trío de color"]

    def test_straight_flush(self):
        label, mult = evaluate_21_plus_3(_hand(Card("9", "♣"), Card("10", "♣")), Card("J", "♣"))
        assert label == "Escalera de color"
        assert mult == TWENTYONE_PLUS_THREE_PAYOUTS["Escalera de color"]

    def test_three_of_a_kind_different_suits(self):
        label, mult = evaluate_21_plus_3(_hand(Card("7", "♥"), Card("7", "♦")), Card("7", "♠"))
        assert label == "Trío"
        assert mult == TWENTYONE_PLUS_THREE_PAYOUTS["Trío"]

    def test_straight_different_suits(self):
        label, mult = evaluate_21_plus_3(_hand(Card("4", "♥"), Card("5", "♦")), Card("6", "♠"))
        assert label == "Escalera"

    def test_ace_low_straight(self):
        """A-2-3 tambien cuenta como escalera (As bajo)."""
        label, mult = evaluate_21_plus_3(_hand(Card("A", "♥"), Card("2", "♦")), Card("3", "♠"))
        assert label == "Escalera"
        assert mult == TWENTYONE_PLUS_THREE_PAYOUTS["Escalera"]

    def test_flush_only(self):
        label, mult = evaluate_21_plus_3(_hand(Card("2", "♦"), Card("7", "♦")), Card("K", "♦"))
        assert label == "Color"

    def test_no_win(self):
        label, mult = evaluate_21_plus_3(_hand(Card("2", "♦"), Card("7", "♥")), Card("K", "♠"))
        assert label == "Sin premio"
        assert mult == 0.0

    def test_missing_dealer_upcard_pays_nothing(self):
        label, mult = evaluate_21_plus_3(_hand(Card("2", "♦"), Card("7", "♦")), None)
        assert mult == 0.0


class TestLuckyLadies:
    def test_queens_of_hearts_pair_is_top_tier(self):
        label, mult = evaluate_lucky_ladies(_hand(Card("Q", "♥"), Card("Q", "♥")))
        assert label == "Damas de corazones"
        assert mult == LUCKY_LADIES_PAYOUTS["Damas de corazones"]

    def test_suited_twenty(self):
        label, mult = evaluate_lucky_ladies(_hand(Card("K", "♠"), Card("Q", "♠")))
        assert label == "Veinte del mismo palo"
        assert mult == LUCKY_LADIES_PAYOUTS["Veinte del mismo palo"]

    def test_any_twenty(self):
        label, mult = evaluate_lucky_ladies(_hand(Card("10", "♦"), Card("10", "♣")))
        assert label == "Veinte cualquiera"
        assert mult == LUCKY_LADIES_PAYOUTS["Veinte cualquiera"]

    def test_ace_counts_as_one_not_eleven(self):
        """Clave de Lucky Ladies: a diferencia del valor normal de la
        mano, aqui el As vale 1 -- As+9 NO debe contar como 20."""
        label, mult = evaluate_lucky_ladies(_hand(Card("A", "♦"), Card("9", "♣")))
        assert label == "Sin premio"
        assert mult == 0.0

    def test_no_win(self):
        label, mult = evaluate_lucky_ladies(_hand(Card("2", "♦"), Card("4", "♣")))
        assert mult == 0.0


class TestRoyalMatch:
    def test_king_queen_suited_is_royal_match(self):
        label, mult = evaluate_royal_match(_hand(Card("K", "♦"), Card("Q", "♦")))
        assert label == "Pareja real"
        assert mult == ROYAL_MATCH_PAYOUTS["Pareja real"]

    def test_any_other_suited_pair(self):
        label, mult = evaluate_royal_match(_hand(Card("5", "♥"), Card("9", "♥")))
        assert label == "Pareja del mismo palo"
        assert mult == ROYAL_MATCH_PAYOUTS["Pareja del mismo palo"]

    def test_different_suits_pays_nothing(self):
        label, mult = evaluate_royal_match(_hand(Card("K", "♦"), Card("Q", "♠")))
        assert mult == 0.0

    def test_king_queen_different_suits_is_not_royal_match(self):
        """K+Q sin ser del mismo palo no debe confundirse con la Pareja
        real -- el palo manda antes que los rangos."""
        label, mult = evaluate_royal_match(_hand(Card("K", "♦"), Card("Q", "♠")))
        assert label == "Sin premio"


class TestSideBetOutcome:
    def test_won_is_true_only_with_positive_multiplier(self):
        win = SideBetOutcome("perfect_pairs", "Pareja perfecta", 25.0, 5.0, 125.0, 130.0)
        lose = SideBetOutcome("perfect_pairs", "Sin pareja", 0.0, 5.0, -5.0, 0.0)
        assert win.won is True
        assert lose.won is False


class TestEngineTracksSideBetWinsForAchievements:
    """Fase 37: GameEngine._resolve_side_bets() debe anotar en
    SessionStats cuántas veces ha ganado cada jugador con Lucky Ladies /
    Royal Match -- es lo que alimentan los logros nuevos "Dama de la
    suerte" / "Pareja real" (ver engine/achievements.py)."""

    def _engine(self):
        from config.rules_presets import vegas_strip
        from engine.game_engine import GameEngine
        rules = vegas_strip()
        rules.lucky_ladies_allowed = True
        rules.royal_match_allowed = True
        return GameEngine(rules=rules, player_name="Test")

    def test_lucky_ladies_win_increments_the_counter(self):
        engine = self._engine()
        player = engine.players[0]
        player.lucky_ladies_bet = 10.0
        hand = _hand(Card("Q", "♥"), Card("Q", "♥"))   # Damas de corazones -- premio máximo
        assert player.stats.lucky_ladies_wins == 0
        engine._resolve_side_bets(0, hand)
        assert player.stats.lucky_ladies_wins == 1

    def test_lucky_ladies_loss_does_not_increment(self):
        engine = self._engine()
        player = engine.players[0]
        player.lucky_ladies_bet = 10.0
        hand = _hand(Card("2", "♣"), Card("4", "♦"))   # suma 6, sin premio
        engine._resolve_side_bets(0, hand)
        assert player.stats.lucky_ladies_wins == 0

    def test_royal_match_win_increments_the_counter(self):
        engine = self._engine()
        player = engine.players[0]
        player.royal_match_bet = 10.0
        hand = _hand(Card("K", "♠"), Card("Q", "♠"))   # Pareja real
        assert player.stats.royal_match_wins == 0
        engine._resolve_side_bets(0, hand)
        assert player.stats.royal_match_wins == 1

    def test_royal_match_loss_does_not_increment(self):
        engine = self._engine()
        player = engine.players[0]
        player.royal_match_bet = 10.0
        hand = _hand(Card("K", "♦"), Card("Q", "♠"))   # distinto palo, sin premio
        engine._resolve_side_bets(0, hand)
        assert player.stats.royal_match_wins == 0
