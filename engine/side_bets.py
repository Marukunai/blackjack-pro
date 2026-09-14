# engine/side_bets.py
# Apuestas laterales opcionales: Parejas Perfectas (Perfect Pairs) y 21+3.
# Se resuelven justo después del reparto inicial (las 2 cartas del
# jugador + la carta visible del crupier), independientemente de cómo
# acabe luego la mano principal.
# -------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.card import Card
    from core.hand import Hand


# ------------------------------------------------------------------
# Parejas Perfectas — evalúa solo las 2 cartas del jugador
# ------------------------------------------------------------------
PERFECT_PAIRS_PAYOUTS: dict[str, float] = {
    "Pareja perfecta": 25.0,   # mismo rango, mismo palo
    "Pareja de color":  12.0,   # mismo rango, mismo color, palo distinto
    "Pareja mixta":      6.0,   # mismo rango, color distinto
}


def evaluate_perfect_pairs(hand: "Hand") -> tuple[str, float]:
    """Devuelve (etiqueta, multiplicador 'a 1'); multiplicador 0.0 si no
    hay premio (no es pareja, o la mano aún no tiene 2 cartas)."""
    if len(hand.cards) < 2:
        return ("Sin pareja", 0.0)
    c1, c2 = hand.cards[0], hand.cards[1]
    if c1.rank != c2.rank:
        return ("Sin pareja", 0.0)
    if c1.suit == c2.suit:
        return ("Pareja perfecta", PERFECT_PAIRS_PAYOUTS["Pareja perfecta"])
    if c1.color == c2.color:
        return ("Pareja de color", PERFECT_PAIRS_PAYOUTS["Pareja de color"])
    return ("Pareja mixta", PERFECT_PAIRS_PAYOUTS["Pareja mixta"])


# ------------------------------------------------------------------
# 21+3 — evalúa las 2 cartas del jugador + la carta visible del
# crupier como una mano de póker de 3 cartas.
# ------------------------------------------------------------------
TWENTYONE_PLUS_THREE_PAYOUTS: dict[str, float] = {
    "Trío de color":     100.0,  # suited trips
    "Escalera de color":  40.0,  # straight flush
    "Trío":                30.0,  # three of a kind
    "Escalera":            10.0,  # straight
    "Color":                5.0,  # flush
}

_RANK_TO_NUM: dict[str, int] = {
    "A": 14, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7,
    "8": 8, "9": 9, "10": 10, "J": 11, "Q": 12, "K": 13,
}


def _is_straight(values: list[int]) -> bool:
    vs = sorted(values)
    if vs[2] - vs[1] == 1 and vs[1] - vs[0] == 1:
        return True
    # As bajo: A-2-3 (el As también vale como 1 para la escalera baja)
    if set(vs) == {14, 2, 3}:
        return True
    return False


def evaluate_21_plus_3(hand: "Hand", dealer_upcard: Optional["Card"]) -> tuple[str, float]:
    """Devuelve (etiqueta, multiplicador 'a 1'); multiplicador 0.0 si no
    hay premio."""
    if len(hand.cards) < 2 or dealer_upcard is None:
        return ("Sin premio", 0.0)

    cards = [hand.cards[0], hand.cards[1], dealer_upcard]
    ranks = [c.rank for c in cards]
    suits = [c.suit for c in cards]
    values = [_RANK_TO_NUM[r] for r in ranks]

    is_flush = len(set(suits)) == 1
    is_trips = len(set(ranks)) == 1
    is_straight = _is_straight(values)

    if is_trips and is_flush:
        return ("Trío de color", TWENTYONE_PLUS_THREE_PAYOUTS["Trío de color"])
    if is_straight and is_flush:
        return ("Escalera de color", TWENTYONE_PLUS_THREE_PAYOUTS["Escalera de color"])
    if is_trips:
        return ("Trío", TWENTYONE_PLUS_THREE_PAYOUTS["Trío"])
    if is_straight:
        return ("Escalera", TWENTYONE_PLUS_THREE_PAYOUTS["Escalera"])
    if is_flush:
        return ("Color", TWENTYONE_PLUS_THREE_PAYOUTS["Color"])
    return ("Sin premio", 0.0)


# ------------------------------------------------------------------
# Resultado combinado, usado por GameEngine para emitir el evento y por
# la UI para mostrar el resultado.
# ------------------------------------------------------------------
@dataclass
class SideBetOutcome:
    kind: str            # "perfect_pairs" | "21+3"
    label: str            # p.ej. "Pareja perfecta", "Sin premio"
    multiplier: float      # 0.0 si no hay premio
    bet: float
    net: float             # ganancia neta (negativa si se pierde la apuesta)
    returned: float        # fichas devueltas en total (0.0 si se pierde)

    @property
    def won(self) -> bool:
        return self.multiplier > 0.0
