# core/hand.py
# Clase Hand: gestión de una mano de Blackjack con cálculo correcto de Ases.
# -------------------------------------------------------------
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.card import Card


class Hand:
    """
    Representa una mano de Blackjack.

    Gestiona el cálculo soft/hard, blackjack natural, bust,
    splits y todas las condiciones de juego.
    """

    def __init__(self, bet: float = 0.0) -> None:
        self.cards: list[Card] = []
        self.bet: float = bet            # apuesta asociada a esta mano
        self.is_doubled: bool = False    # True si se hizo Double Down
        self.is_split: bool = False      # True si proviene de un Split
        self.stood: bool = False         # True si el jugador plantó
        self.surrendered: bool = False   # True si el jugador se rindió

    # ------------------------------------------------------------------
    # Añadir cartas
    # ------------------------------------------------------------------
    def add_card(self, card: Card) -> None:
        self.cards.append(card)

    def clear(self) -> None:
        self.cards.clear()
        self.bet = 0.0
        self.is_doubled = False
        self.is_split = False
        self.stood = False
        self.surrendered = False

    # ------------------------------------------------------------------
    # Cálculo de valor (núcleo del juego)
    # ------------------------------------------------------------------
    @property
    def value(self) -> int:
        """
        Valor óptimo de la mano (máximo sin pasarse de 21).
        Los Ases cuentan como 11 hasta que la mano se pase; entonces como 1.
        """
        total = 0
        aces = 0

        for card in self.cards:
            if not card.face_up:
                continue          # ignorar cartas boca abajo (hole card)
            if card.is_ace:
                aces += 1
                total += 11
            else:
                total += card.value

        # Reducir Ases de 11 → 1 mientras nos pasemos
        while total > 21 and aces:
            total -= 10
            aces -= 1

        return total

    @property
    def value_with_hidden(self) -> int:
        """Valor contando TODAS las cartas, incluyendo las boca abajo (uso interno)."""
        total = 0
        aces = 0
        for card in self.cards:
            if card.is_ace:
                aces += 1
                total += 11
            else:
                total += card.value
        while total > 21 and aces:
            total -= 10
            aces -= 1
        return total

    @property
    def is_soft(self) -> bool:
        """True si la mano tiene un As que cuenta como 11 (soft hand)."""
        total = 0
        aces = 0
        for card in self.cards:
            if not card.face_up:
                continue
            if card.is_ace:
                aces += 1
                total += 11
            else:
                total += card.value
        while total > 21 and aces:
            total -= 10
            aces -= 1
        # Si queda algún As contando como 11 → soft
        return aces > 0 and total <= 21

    @property
    def is_hard(self) -> bool:
        return not self.is_soft

    # ------------------------------------------------------------------
    # Estados de la mano
    # ------------------------------------------------------------------
    @property
    def is_bust(self) -> bool:
        return self.value > 21

    @property
    def is_blackjack(self) -> bool:
        """Natural: exactamente 2 cartas y valor 21 (sin ser de split)."""
        return len(self.cards) == 2 and self.value == 21 and not self.is_split

    @property
    def is_twenty_one(self) -> bool:
        """21 con más de 2 cartas (no es blackjack natural)."""
        return self.value == 21 and not self.is_blackjack

    @property
    def is_pair(self) -> bool:
        """True si la mano tiene exactamente 2 cartas del mismo rango."""
        return len(self.cards) == 2 and self.cards[0].rank == self.cards[1].rank

    @property
    def is_pair_of_aces(self) -> bool:
        return self.is_pair and self.cards[0].is_ace

    @property
    def can_split(self) -> bool:
        return self.is_pair and not self.surrendered

    @property
    def can_double(self) -> bool:
        """Se puede doblar con exactamente 2 cartas y sin haberse rendido."""
        return len(self.cards) == 2 and not self.surrendered and not self.is_doubled

    @property
    def is_finished(self) -> bool:
        """La mano ya no admite más acciones."""
        return (
            self.is_bust
            or self.stood
            or self.surrendered
            or self.is_blackjack
            or self.is_doubled        # tras doblar solo se recibe 1 carta más → stood implícito
            or self.value == 21
        )

    @property
    def card_count(self) -> int:
        return len(self.cards)

    # ------------------------------------------------------------------
    # Representación
    # ------------------------------------------------------------------
    def __str__(self) -> str:
        cards_str = " ".join(str(c) for c in self.cards)
        soft_tag = " (soft)" if self.is_soft else ""
        bj_tag = " ★ BLACKJACK" if self.is_blackjack else ""
        bust_tag = " ✗ BUST" if self.is_bust else ""
        return f"[{cards_str}] = {self.value}{soft_tag}{bj_tag}{bust_tag}  bet={self.bet:.0f}"

    def __repr__(self) -> str:
        return f"Hand(value={self.value}, cards={len(self.cards)}, bet={self.bet})"