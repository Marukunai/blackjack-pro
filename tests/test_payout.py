# tests/test_payout.py
import pytest
from core.card import Card
from core.hand import Hand
from core.dealer import Dealer
from core.rules import Rules, BlackjackPayout, SurrenderRule
from engine.game_state import RoundResult
from engine.payout import resolve_hand


def dealer_with(*rank_suit_pairs) -> Dealer:
    d = Dealer()
    for rank, suit in rank_suit_pairs:
        d.add_card(Card(rank, suit))
    return d


def hand_with(bet=10.0, *rank_suit_pairs) -> Hand:
    h = Hand(bet=bet)
    for rank, suit in rank_suit_pairs:
        h.add_card(Card(rank, suit))
    return h


rules = Rules()


class TestPlayerBust:
    def test_player_bust_loses(self):
        h = hand_with(10.0, ("K", "♠"), ("Q", "♥"), ("5", "♦"))
        d = dealer_with(("7", "♠"), ("9", "♥"))
        p = resolve_hand(h, d, rules)
        assert p.result == RoundResult.LOSS
        assert p.net == -10.0


class TestBlackjackPayout:
    def test_blackjack_3to2(self):
        h = hand_with(10.0, ("A", "♠"), ("K", "♥"))
        d = dealer_with(("7", "♠"), ("9", "♥"))
        p = resolve_hand(h, d, rules)
        assert p.result == RoundResult.BLACKJACK_WIN
        assert p.net == 15.0

    def test_blackjack_6to5(self):
        r = Rules(blackjack_payout=BlackjackPayout.SIX_TO_FIVE)
        h = hand_with(10.0, ("A", "♠"), ("K", "♥"))
        d = dealer_with(("7", "♠"), ("9", "♥"))
        p = resolve_hand(h, d, r)
        assert p.result == RoundResult.BLACKJACK_WIN
        assert p.net == 12.0

    def test_blackjack_vs_blackjack_is_push(self):
        h = hand_with(10.0, ("A", "♠"), ("K", "♥"))
        d = dealer_with(("A", "♦"), ("Q", "♣"))
        p = resolve_hand(h, d, rules)
        assert p.result == RoundResult.PUSH
        assert p.net == 0.0


class TestWinLosePush:
    def test_player_wins(self):
        h = hand_with(10.0, ("K", "♠"), ("9", "♥"))   # 19
        d = dealer_with(("K", "♦"), ("7", "♣"))         # 17
        p = resolve_hand(h, d, rules)
        assert p.result == RoundResult.WIN
        assert p.net == 10.0

    def test_player_loses(self):
        h = hand_with(10.0, ("7", "♠"), ("9", "♥"))   # 16
        d = dealer_with(("K", "♦"), ("9", "♣"))         # 19
        p = resolve_hand(h, d, rules)
        assert p.result == RoundResult.LOSS
        assert p.net == -10.0

    def test_push(self):
        h = hand_with(10.0, ("K", "♠"), ("8", "♥"))   # 18
        d = dealer_with(("K", "♦"), ("8", "♣"))         # 18
        p = resolve_hand(h, d, rules)
        assert p.result == RoundResult.PUSH
        assert p.net == 0.0


class TestDealerBust:
    def test_dealer_bust_player_wins(self):
        h = hand_with(10.0, ("K", "♠"), ("8", "♥"))   # 18
        d = dealer_with(("K", "♦"), ("Q", "♣"), ("5", "♠"))  # 25
        p = resolve_hand(h, d, rules)
        assert p.result == RoundResult.DEALER_BUST
        assert p.net == 10.0


class TestSurrender:
    def test_surrender_returns_half(self):
        h = hand_with(10.0, ("K", "♠"), ("6", "♥"))
        h.surrendered = True
        h.stood = True
        d = dealer_with(("9", "♦"), ("7", "♣"))
        p = resolve_hand(h, d, rules)
        assert p.result == RoundResult.SURRENDER
        assert p.returned == 5.0
        assert p.net == -5.0