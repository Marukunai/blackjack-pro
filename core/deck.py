# core/deck.py
# Clase Deck: uno o más mazos de 52 cartas, barajado y penetración de corte.
# -------------------------------------------------------------
from __future__ import annotations

import random
from typing import Optional

from core.card import Card, SUITS, RANKS


class Deck:
    """
    Zapato (shoe) de N mazos estándar de 52 cartas.

    Parámetros
    ----------
    num_decks : int
        Número de mazos (1, 2, 4, 6 u 8).
    penetration : float
        Fracción del zapato que se reparte antes de rebarajar (0.5 – 0.9).
        Por defecto 0.75 (75 % de penetración, típico de casino).
    seed : int | None
        Semilla para reproducibilidad en tests.
    """

    VALID_DECK_COUNTS = (1, 2, 4, 6, 8)

    def __init__(
        self,
        num_decks: int = 6,
        penetration: float = 0.75,
        seed: Optional[int] = None,
    ) -> None:
        if num_decks not in self.VALID_DECK_COUNTS:
            raise ValueError(f"num_decks debe ser uno de {self.VALID_DECK_COUNTS}")
        if not (0.5 <= penetration <= 0.95):
            raise ValueError("penetration debe estar entre 0.5 y 0.95")

        self.num_decks = num_decks
        self.penetration = penetration
        self._rng = random.Random(seed)

        self._cards: list[Card] = []
        self._cut_card_position: int = 0   # índice donde está la tarjeta de corte
        self.reshuffle_flag: bool = False   # se activa cuando se supera el corte

        self._build_and_shuffle()

    # ------------------------------------------------------------------
    # Construcción
    # ------------------------------------------------------------------
    def _build_and_shuffle(self) -> None:
        """Reconstruye el zapato completo y lo baraja."""
        self._cards = [
            Card(rank=rank, suit=suit)
            for _ in range(self.num_decks)
            for suit in SUITS
            for rank in RANKS
        ]
        self._rng.shuffle(self._cards)
        # La tarjeta de corte se coloca en el último (1-penetration) del zapato
        total = len(self._cards)
        self._cut_card_position = int(total * self.penetration)
        self.reshuffle_flag = False

    def shuffle(self) -> None:
        """Permite rebarajar manualmente (llama a _build_and_shuffle)."""
        self._build_and_shuffle()

    # ------------------------------------------------------------------
    # Reparto
    # ------------------------------------------------------------------
    def deal(self) -> Card:
        """
        Extrae y devuelve la carta de arriba del zapato.
        Si el zapato está vacío rebaraja automáticamente.
        Activa reshuffle_flag cuando se pasa la tarjeta de corte.
        """
        if not self._cards:
            self._build_and_shuffle()

        card = self._cards.pop()

        # ¿Hemos superado la tarjeta de corte?
        dealt_count = self.total_cards - len(self._cards)
        if dealt_count >= self._cut_card_position:
            self.reshuffle_flag = True

        return card

    def deal_hidden(self) -> Card:
        """Reparte una carta boca abajo (hole card del crupier)."""
        card = self.deal()
        card.hide()
        return card

    # ------------------------------------------------------------------
    # Propiedades informativas
    # ------------------------------------------------------------------
    @property
    def total_cards(self) -> int:
        return self.num_decks * 52

    @property
    def cards_remaining(self) -> int:
        return len(self._cards)

    @property
    def cards_dealt(self) -> int:
        return self.total_cards - self.cards_remaining

    @property
    def penetration_reached(self) -> bool:
        return self.reshuffle_flag

    @property
    def remaining_fraction(self) -> float:
        """Fracción de cartas que quedan en el zapato (0.0 – 1.0)."""
        return self.cards_remaining / self.total_cards

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------
    def __len__(self) -> int:
        return self.cards_remaining

    def __repr__(self) -> str:
        return (
            f"Deck(num_decks={self.num_decks}, "
            f"remaining={self.cards_remaining}/{self.total_cards}, "
            f"penetration={self.penetration:.0%})"
        )