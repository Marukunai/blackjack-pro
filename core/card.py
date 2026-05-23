# core/card.py
# Clase Card: representa una carta individual de la baraja francesa.
# -------------------------------------------------------------
from __future__ import annotations
from dataclasses import dataclass, field
from typing import ClassVar


SUITS = ("♠", "♥", "♦", "♣")
SUIT_NAMES = {"♠": "Spades", "♥": "Hearts", "♦": "Diamonds", "♣": "Clubs"}
RANKS = ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K")

# Valor numérico de cada rango (el As se gestiona en Hand)
RANK_VALUES: dict[str, int] = {
    "A": 11, "2": 2, "3": 3, "4": 4, "5": 5,
    "6": 6,  "7": 7, "8": 8, "9": 9, "10": 10,
    "J": 10, "Q": 10, "K": 10,
}

# Nombre de imagen del asset (p.ej. "AH.png", "10S.png")
SUIT_ASSET_LETTER = {"♠": "S", "♥": "H", "♦": "D", "♣": "C"}


@dataclass
class Card:
    """Una carta de la baraja: rango + palo."""

    rank: str          # "A", "2" … "10", "J", "Q", "K"
    suit: str          # "♠", "♥", "♦", "♣"
    face_up: bool = field(default=True, compare=False)

    # Referencia rápida a la tabla de valores (compartida entre instancias)
    _value_table: ClassVar[dict[str, int]] = RANK_VALUES

    # ------------------------------------------------------------------
    # Propiedades
    # ------------------------------------------------------------------
    @property
    def value(self) -> int:
        """Valor base de la carta (el As devuelve 11; Hand lo ajusta)."""
        return self._value_table[self.rank]

    @property
    def is_ace(self) -> bool:
        return self.rank == "A"

    @property
    def is_face_card(self) -> bool:
        return self.rank in ("J", "Q", "K")

    @property
    def is_ten_valued(self) -> bool:
        """Devuelve True para 10, J, Q, K."""
        return self.value == 10

    @property
    def asset_name(self) -> str:
        """Nombre del archivo de imagen, p.ej. 'AH.png', '10S.png'."""
        return f"{self.rank}{SUIT_ASSET_LETTER[self.suit]}.png"

    @property
    def color(self) -> str:
        """'red' para corazones/diamantes, 'black' para picas/tréboles."""
        return "red" if self.suit in ("♥", "♦") else "black"

    # ------------------------------------------------------------------
    # Representación
    # ------------------------------------------------------------------
    def __str__(self) -> str:
        if not self.face_up:
            return "🂠 [hidden]"
        return f"{self.rank}{self.suit}"

    def __repr__(self) -> str:
        return f"Card(rank={self.rank!r}, suit={self.suit!r}, face_up={self.face_up})"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def flip(self) -> None:
        """Voltea la carta (boca arriba ↔ boca abajo)."""
        self.face_up = not self.face_up

    def reveal(self) -> None:
        """Pone la carta boca arriba."""
        self.face_up = True

    def hide(self) -> None:
        """Pone la carta boca abajo."""
        self.face_up = False