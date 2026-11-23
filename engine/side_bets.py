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
# Lucky Ladies (Fase 31) — evalúa solo las 2 cartas del jugador. A
# diferencia del valor normal de la mano, aquí el As vale 1 (no 11):
# así un As+9 NO cuenta como "20", igual que en las mesas reales.
# ------------------------------------------------------------------
LUCKY_LADIES_PAYOUTS: dict[str, float] = {
    "Damas de corazones":    100.0,  # pareja de Reinas de Corazones (QH+QH)
    "Veinte del mismo palo":  15.0,  # 2 cartas del mismo palo que suman 20
    "Veinte cualquiera":       4.0,  # cualquier par de cartas que suma 20
}

_LUCKY_LADIES_VALUE: dict[str, int] = {
    "A": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7,
    "8": 8, "9": 9, "10": 10, "J": 10, "Q": 10, "K": 10,
}


def evaluate_lucky_ladies(hand: "Hand") -> tuple[str, float]:
    """Devuelve (etiqueta, multiplicador 'a 1') para Lucky Ladies."""
    if len(hand.cards) < 2:
        return ("Sin premio", 0.0)
    c1, c2 = hand.cards[0], hand.cards[1]

    if c1.rank == "Q" and c2.rank == "Q" and c1.suit == "♥" and c2.suit == "♥":
        return ("Damas de corazones", LUCKY_LADIES_PAYOUTS["Damas de corazones"])

    total = _LUCKY_LADIES_VALUE[c1.rank] + _LUCKY_LADIES_VALUE[c2.rank]
    if total == 20:
        if c1.suit == c2.suit:
            return ("Veinte del mismo palo", LUCKY_LADIES_PAYOUTS["Veinte del mismo palo"])
        return ("Veinte cualquiera", LUCKY_LADIES_PAYOUTS["Veinte cualquiera"])
    return ("Sin premio", 0.0)


# ------------------------------------------------------------------
# Royal Match (Fase 31) — evalúa solo las 2 cartas del jugador: premia
# que sean del mismo palo, y más si son concretamente Rey+Reina.
# ------------------------------------------------------------------
ROYAL_MATCH_PAYOUTS: dict[str, float] = {
    "Pareja real":           25.0,  # K + Q del mismo palo (el "Royal Match")
    "Pareja del mismo palo":  5.0,  # cualquier otro par de cartas del mismo palo
}


def evaluate_royal_match(hand: "Hand") -> tuple[str, float]:
    """Devuelve (etiqueta, multiplicador 'a 1') para Royal Match."""
    if len(hand.cards) < 2:
        return ("Sin premio", 0.0)
    c1, c2 = hand.cards[0], hand.cards[1]
    if c1.suit != c2.suit:
        return ("Sin premio", 0.0)
    if {c1.rank, c2.rank} == {"K", "Q"}:
        return ("Pareja real", ROYAL_MATCH_PAYOUTS["Pareja real"])
    return ("Pareja del mismo palo", ROYAL_MATCH_PAYOUTS["Pareja del mismo palo"])


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
