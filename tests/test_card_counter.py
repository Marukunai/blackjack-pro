# tests/test_card_counter.py
# Cobertura de ai/card_counter.py (HiLoCounter), que sostiene tanto la
# insignia de conteo en vivo como el modo de practica de conteo de
# cartas (Fase 30) -- ninguno de los dos tenia tests permanentes.
from __future__ import annotations

from core.card import Card
from ai.card_counter import HiLoCounter, HI_LO_VALUES


class _FakeDeck:
    def __init__(self, cards_remaining: int) -> None:
        self.cards_remaining = cards_remaining


class TestHiLoValues:
    def test_low_cards_are_plus_one(self):
        for rank in ("2", "3", "4", "5", "6"):
            assert HI_LO_VALUES[rank] == 1

    def test_neutral_cards_are_zero(self):
        for rank in ("7", "8", "9"):
            assert HI_LO_VALUES[rank] == 0

    def test_high_cards_are_minus_one(self):
        for rank in ("10", "J", "Q", "K", "A"):
            assert HI_LO_VALUES[rank] == -1


class TestRunningCount:
    def test_starts_at_zero(self):
        assert HiLoCounter().running_count == 0

    def test_face_up_cards_update_the_count(self):
        counter = HiLoCounter()
        counter.register_card(Card("5", "♠"))   # +1
        counter.register_card(Card("K", "♦"))   # -1
        counter.register_card(Card("8", "♣"))   # 0
        assert counter.running_count == 0

    def test_face_down_cards_are_ignored(self):
        counter = HiLoCounter()
        hidden = Card("5", "♠", face_up=False)
        counter.register_card(hidden)
        assert counter.running_count == 0

    def test_reset_clears_running_count_only(self):
        counter = HiLoCounter()
        counter.register_card(Card("2", "♠"))
        counter.update_deck_estimate(_FakeDeck(cards_remaining=104))
        counter.reset()
        assert counter.running_count == 0


class TestTrueCount:
    def test_true_count_divides_by_decks_remaining(self):
        counter = HiLoCounter()
        for _ in range(6):
            counter.register_card(Card("2", "♠"))   # running_count = 6
        counter.update_deck_estimate(_FakeDeck(cards_remaining=156))  # 3 mazos
        assert counter.true_count == 2.0

    def test_deck_estimate_never_drops_below_half_a_deck(self):
        """Evita division por (casi) cero cuando el zapato esta casi
        vacio -- medio mazo es el piso."""
        counter = HiLoCounter()
        counter.register_card(Card("2", "♠"))
        counter.update_deck_estimate(_FakeDeck(cards_remaining=1))
        assert counter.true_count == 2.0   # 1 / 0.5


class TestSuggestedBet:
    def _counter_with_true_count(self, tc: int) -> HiLoCounter:
        counter = HiLoCounter()
        for _ in range(tc):
            counter.register_card(Card("2", "♠"))
        counter.update_deck_estimate(_FakeDeck(cards_remaining=52))  # 1 mazo
        return counter

    def test_low_or_negative_count_bets_minimum(self):
        counter = self._counter_with_true_count(0)
        assert counter.suggested_bet_units(min_bet=10.0) == 10.0

    def test_true_count_two_doubles_the_bet(self):
        counter = self._counter_with_true_count(2)
        assert counter.suggested_bet_units(min_bet=10.0) == 20.0

    def test_true_count_three_or_four_quadruples_the_bet(self):
        counter = self._counter_with_true_count(3)
        assert counter.suggested_bet_units(min_bet=10.0) == 40.0

    def test_true_count_five_plus_caps_at_eight_units(self):
        counter = self._counter_with_true_count(8)
        assert counter.suggested_bet_units(min_bet=10.0) == 80.0


class TestLabelsAndColors:
    def test_every_true_count_bucket_has_a_label_and_color(self):
        for tc in (-5, -2, -1, 0, 1, 2, 3, 6):
            counter = HiLoCounter()
            counter.running_count = tc
            counter.update_deck_estimate(_FakeDeck(cards_remaining=52))  # 1 mazo
            assert isinstance(counter.count_label, str) and counter.count_label
            assert counter.count_color.startswith("#")
