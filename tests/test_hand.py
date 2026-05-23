# tests/test_hand.py
import pytest
from core.card import Card
from core.hand import Hand


def make_hand(*rank_suit_pairs) -> Hand:
    h = Hand()
    for rank, suit in rank_suit_pairs:
        h.add_card(Card(rank, suit))
    return h


class TestHandValue:
    def test_simple_values(self):
        h = make_hand(("7", "♠"), ("8", "♥"))
        assert h.value == 15

    def test_face_cards_are_ten(self):
        h = make_hand(("K", "♠"), ("Q", "♥"))
        assert h.value == 20

    def test_ace_counts_as_11(self):
        h = make_hand(("A", "♠"), ("9", "♥"))
        assert h.value == 20

    def test_ace_reduced_to_one_on_bust(self):
        h = make_hand(("A", "♠"), ("9", "♥"), ("5", "♦"))
        assert h.value == 15   # A+9+5 → 11+9+5=25 → 1+9+5=15

    def test_two_aces(self):
        h = make_hand(("A", "♠"), ("A", "♥"))
        assert h.value == 12   # 11+1

    def test_three_aces(self):
        h = make_hand(("A", "♠"), ("A", "♥"), ("A", "♦"))
        assert h.value == 13   # 11+1+1


class TestBlackjack:
    def test_natural_blackjack(self):
        h = make_hand(("A", "♠"), ("K", "♥"))
        assert h.is_blackjack

    def test_21_with_three_cards_is_not_blackjack(self):
        h = make_hand(("7", "♠"), ("7", "♥"), ("7", "♦"))
        assert not h.is_blackjack
        assert h.value == 21

    def test_split_hand_blackjack_is_false(self):
        h = make_hand(("A", "♠"), ("K", "♥"))
        h.is_split = True
        assert not h.is_blackjack


class TestBust:
    def test_bust(self):
        h = make_hand(("K", "♠"), ("Q", "♥"), ("5", "♦"))
        assert h.is_bust

    def test_not_bust(self):
        h = make_hand(("K", "♠"), ("Q", "♥"))
        assert not h.is_bust


class TestSoft:
    def test_soft_hand(self):
        h = make_hand(("A", "♠"), ("6", "♥"))
        assert h.is_soft
        assert h.value == 17

    def test_hard_hand(self):
        h = make_hand(("10", "♠"), ("7", "♥"))
        assert h.is_hard

    def test_ace_forced_hard(self):
        h = make_hand(("A", "♠"), ("9", "♥"), ("5", "♦"))
        assert h.is_hard   # 1+9+5 = 15, el As no puede ser 11


class TestPair:
    def test_pair(self):
        h = make_hand(("8", "♠"), ("8", "♥"))
        assert h.is_pair

    def test_no_pair(self):
        h = make_hand(("8", "♠"), ("9", "♥"))
        assert not h.is_pair

    def test_pair_of_aces(self):
        h = make_hand(("A", "♠"), ("A", "♥"))
        assert h.is_pair_of_aces


class TestActions:
    def test_can_double_with_two_cards(self):
        h = make_hand(("5", "♠"), ("6", "♥"))
        assert h.can_double

    def test_cannot_double_after_hit(self):
        h = make_hand(("5", "♠"), ("6", "♥"), ("4", "♦"))
        assert not h.can_double

    def test_finished_after_bust(self):
        h = make_hand(("K", "♠"), ("Q", "♥"), ("5", "♦"))
        assert h.is_finished

    def test_finished_after_stand(self):
        h = make_hand(("K", "♠"), ("7", "♥"))
        h.stood = True
        assert h.is_finished