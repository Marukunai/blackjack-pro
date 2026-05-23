# ai/card_counter.py
# Contador de cartas Hi-Lo con true count y nivel de apuesta sugerido.
# -------------------------------------------------------------
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.card import Card
    from core.deck import Deck


# Valores Hi-Lo por rango
HI_LO_VALUES: dict[str, int] = {
    "2": +1, "3": +1, "4": +1, "5": +1, "6": +1,
    "7":  0, "8":  0, "9":  0,
    "10": -1, "J": -1, "Q": -1, "K": -1, "A": -1,
}


class HiLoCounter:
    """
    Implementa el sistema de conteo Hi-Lo.

    running_count : conteo acumulado desde el último barajado
    true_count    : running_count / mazos restantes (más preciso)
    """

    def __init__(self) -> None:
        self.running_count: int = 0
        self._decks_estimate: float = 6.0   # se actualiza desde el deck

    def reset(self) -> None:
        """Resetear al barajar."""
        self.running_count = 0

    def register_card(self, card: "Card") -> None:
        """Actualiza el running count al ver una carta."""
        if card.face_up:
            self.running_count += HI_LO_VALUES.get(card.rank, 0)

    def update_deck_estimate(self, deck: "Deck") -> None:
        """Recibe el deck para calcular mazos restantes."""
        self._decks_estimate = max(0.5, deck.cards_remaining / 52)

    @property
    def true_count(self) -> float:
        """True count = running count / mazos restantes."""
        return self.running_count / self._decks_estimate

    @property
    def true_count_rounded(self) -> int:
        return round(self.true_count)

    # ------------------------------------------------------------------
    # Ventaja estimada del jugador
    # ------------------------------------------------------------------
    @property
    def player_edge(self) -> float:
        """
        Estimación del edge del jugador en %.
        Base house edge ~0.5%, cada punto de true count ≈ +0.5%.
        """
        base_edge = -0.5
        return base_edge + (self.true_count * 0.5)

    # ------------------------------------------------------------------
    # Sugerencia de apuesta (bet spread 1-12)
    # ------------------------------------------------------------------
    def suggested_bet_units(self, min_bet: float) -> float:
        """
        Devuelve un multiplicador de apuesta basado en el true count.
        True count ≤ 1  → 1 unidad (apuesta mínima)
        True count 2    → 2 unidades
        True count 3-4  → 4 unidades
        True count 5+   → 8 unidades (techo conservador)
        """
        tc = self.true_count_rounded
        if tc <= 1:
            units = 1
        elif tc == 2:
            units = 2
        elif tc in (3, 4):
            units = 4
        else:
            units = 8
        return min_bet * units

    # ------------------------------------------------------------------
    # Etiqueta visual
    # ------------------------------------------------------------------
    @property
    def count_label(self) -> str:
        tc = self.true_count_rounded
        if tc <= -2:
            return "Muy frío 🥶"
        elif tc == -1:
            return "Frío ❄️"
        elif tc == 0:
            return "Neutral ➖"
        elif tc == 1:
            return "Tibio 🌡️"
        elif tc in (2, 3):
            return "Caliente 🔥"
        else:
            return "¡Muy caliente! 🌋"

    @property
    def count_color(self) -> str:
        """Color hex para la UI."""
        tc = self.true_count_rounded
        if tc >= 3:
            return "#E74C3C"   # rojo caliente
        elif tc >= 1:
            return "#F39C12"   # naranja
        elif tc == 0:
            return "#BDC3C7"   # gris
        else:
            return "#2980B9"   # azul frío

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------
    def __str__(self) -> str:
        return (
            f"Hi-Lo | RC={self.running_count:+d} | "
            f"TC={self.true_count:+.1f} | "
            f"{self.count_label}"
        )

    def __repr__(self) -> str:
        return f"HiLoCounter(rc={self.running_count}, tc={self.true_count:.2f})"