# tests/test_deck.py
import pytest
from core.deck import Deck
from core.card import SUITS, RANKS


class TestDeckInit:
    def test_six_deck_size(self):
        d = Deck(num_decks=6)
        assert len(d) == 6 * 52

    def test_single_deck_size(self):
        d = Deck(num_decks=1)
        assert len(d) == 52

    def test_invalid_deck_count(self):
        with pytest.raises(ValueError):
            Deck(num_decks=3)

    def test_invalid_penetration(self):
        with pytest.raises(ValueError):
            Deck(num_decks=6, penetration=0.1)


class TestDeckDeal:
    def test_deal_reduces_count(self):
        d = Deck(num_decks=1, seed=42)
        initial = len(d)
        d.deal()
        assert len(d) == initial - 1

    def test_deal_hidden_is_face_down(self):
        d = Deck(num_decks=1, seed=42)
        card = d.deal_hidden()
        assert not card.face_up

    def test_deal_face_up_by_default(self):
        d = Deck(num_decks=1, seed=42)
        card = d.deal()
        assert card.face_up

    def test_all_cards_dealt_triggers_reshuffle(self):
        d = Deck(num_decks=1, penetration=0.95, seed=42)
        # Repartir suficientes como para superar el corte
        for _ in range(50):
            d.deal()
        assert d.penetration_reached


class TestDeckShuffle:
    def test_shuffle_resets_count(self):
        d = Deck(num_decks=1, seed=1)
        for _ in range(20):
            d.deal()
        d.shuffle()
        assert len(d) == 52
        assert not d.penetration_reached

    def test_deterministic_with_seed(self):
        d1 = Deck(num_decks=1, seed=99)
        d2 = Deck(num_decks=1, seed=99)
        cards1 = [d1.deal().rank + d1.deal().suit for _ in range(5)]
        cards2 = [d2.deal().rank + d2.deal().suit for _ in range(5)]
        # Con la misma semilla deben salir en el mismo orden
        # (nota: cada deal consume 1 carta, así que reajustamos)
        d1 = Deck(num_decks=1, seed=99)
        d2 = Deck(num_decks=1, seed=99)
        assert [str(d1.deal()) for _ in range(5)] == [str(d2.deal()) for _ in range(5)]