# core/dealer.py
# Clase Dealer: hereda Hand, aplica la lógica S17 / H17 del crupier.
# -------------------------------------------------------------
from __future__ import annotations

from core.hand import Hand
from core.rules import DealerRule, Rules


class Dealer:
    """
    Representa al crupier.

    El crupier tiene exactamente una mano y sigue reglas fijas
    (no toma decisiones: siempre pide hasta alcanzar su umbral).
    """

    def __init__(self) -> None:
        self.hand: Hand = Hand()

    # ------------------------------------------------------------------
    # Cartas
    # ------------------------------------------------------------------
    def reset(self) -> None:
        self.hand.clear()

    def add_card(self, card) -> None:
        self.hand.add_card(card)

    def reveal_hole_card(self) -> None:
        """Muestra la carta boca abajo (hole card) al final del turno."""
        for card in self.hand.cards:
            card.reveal()

    # ------------------------------------------------------------------
    # Lógica de juego automática
    # ------------------------------------------------------------------
    def must_hit(self, rules: Rules) -> bool:
        """
        Devuelve True si el crupier DEBE pedir carta según las reglas.

        S17 → planta en soft 17 (el crupier NO pide)
        H17 → pide en soft 17  (el crupier SÍ pide)
        Siempre pide con valor < 17.
        Nunca pide con valor > 17 ni si está bust.
        """
        v = self.hand.value_with_hidden

        if v > 21:      # bust
            return False
        if v > 17:      # 18, 19, 20, 21 → siempre planta
            return False
        if v < 17:      # 16 o menos → siempre pide
            return True

        # v == 17 exactamente
        if self.hand.is_soft:
            # Soft 17 (p.ej. A+6)
            return rules.dealer_rule == DealerRule.HIT_SOFT_17
        else:
            # Hard 17 → siempre planta
            return False

    # ------------------------------------------------------------------
    # Propiedades de conveniencia
    # ------------------------------------------------------------------
    @property
    def upcard(self):
        """La carta visible del crupier (la primera boca arriba)."""
        for card in self.hand.cards:
            if card.face_up:
                return card
        return None

    @property
    def upcard_value(self) -> int:
        card = self.upcard
        return card.value if card else 0

    @property
    def showing_ace(self) -> bool:
        return self.upcard is not None and self.upcard.is_ace

    @property
    def showing_ten(self) -> bool:
        return self.upcard is not None and self.upcard.is_ten_valued

    @property
    def has_blackjack(self) -> bool:
        return self.hand.value_with_hidden == 21 and len(self.hand.cards) == 2

    @property
    def is_bust(self) -> bool:
        return self.hand.value_with_hidden > 21

    @property
    def value(self) -> int:
        return self.hand.value_with_hidden

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------
    def __str__(self) -> str:
        upcard = self.upcard
        up_str = str(upcard) if upcard else "?"
        return f"Dealer [upcard={up_str}, hand={self.hand}]"

    def __repr__(self) -> str:
        return f"Dealer(value={self.value}, cards={len(self.hand.cards)})"