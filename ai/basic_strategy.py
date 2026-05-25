# ai/basic_strategy.py
# Tabla de estrategia básica completa para Blackjack.
# Cubre hard totals, soft totals y pares para cualquier upcard del crupier.
# -------------------------------------------------------------
from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.hand import Hand
    from core.rules import Rules


class BasicAction(Enum):
    H  = "Hit"
    S  = "Stand"
    D  = "Double (else Hit)"
    DS = "Double (else Stand)"
    P  = "Split"
    PH = "Split (else Hit)"
    R  = "Surrender (else Hit)"
    RS = "Surrender (else Stand)"
    RP = "Surrender (else Split)"


# ------------------------------------------------------------------
# Tablas de estrategia básica
# Eje X: upcard del crupier (2..10, A)
# Eje Y: total del jugador
# Basadas en 4-8 mazos, S17, DAS, Late Surrender (Vegas Strip estándar)
# ------------------------------------------------------------------

UPCARD_INDEX = {2: 0, 3: 1, 4: 2, 5: 3, 6: 4, 7: 5, 8: 6, 9: 7, 10: 8, 11: 9}

# Aliases para las tablas (deben estar antes de los dicts)
H  = BasicAction.H
S  = BasicAction.S
D  = BasicAction.D
DS = BasicAction.DS
P  = BasicAction.P
PH = BasicAction.PH
R  = BasicAction.R
RS = BasicAction.RS
RP = BasicAction.RP

# --- HARD TOTALS (8..17+) ---
# Columnas: crupier 2,3,4,5,6,7,8,9,10,A
HARD: dict[int, list[BasicAction]] = {
    # total: [crupier 2 … A]
    4:  [H,  H,  H,  H,  H,  H,  H,  H,  H,  H ],
    5:  [H,  H,  H,  H,  H,  H,  H,  H,  H,  H ],
    6:  [H,  H,  H,  H,  H,  H,  H,  H,  H,  H ],
    7:  [H,  H,  H,  H,  H,  H,  H,  H,  H,  H ],
    8:  [H,  H,  H,  H,  H,  H,  H,  H,  H,  H ],
    9:  [H,  D,  D,  D,  D,  H,  H,  H,  H,  H ],
    10: [D,  D,  D,  D,  D,  D,  D,  D,  H,  H ],
    11: [D,  D,  D,  D,  D,  D,  D,  D,  D,  H ],
    12: [H,  H,  S,  S,  S,  H,  H,  H,  H,  H ],
    13: [S,  S,  S,  S,  S,  H,  H,  H,  H,  H ],
    14: [S,  S,  S,  S,  S,  H,  H,  H,  H,  H ],
    15: [S,  S,  S,  S,  S,  H,  H,  H,  R,  H ],
    16: [S,  S,  S,  S,  S,  H,  H,  R,  R,  R ],
    17: [S,  S,  S,  S,  S,  S,  S,  S,  S,  RS],
}
# 18+ siempre Stand

# --- SOFT TOTALS (A+2 … A+9) --- (valor total 13..21)
# Columnas: crupier 2,3,4,5,6,7,8,9,10,A
SOFT: dict[int, list[BasicAction]] = {
    # total (incluyendo el As como 11):
    13: [H,  H,  H,  D,  D,  H,  H,  H,  H,  H ],  # A+2
    14: [H,  H,  H,  D,  D,  H,  H,  H,  H,  H ],  # A+3
    15: [H,  H,  D,  D,  D,  H,  H,  H,  H,  H ],  # A+4
    16: [H,  H,  D,  D,  D,  H,  H,  H,  H,  H ],  # A+5
    17: [H,  D,  D,  D,  D,  H,  H,  H,  H,  H ],  # A+6
    18: [DS, DS, DS, DS, DS, S,  S,  H,  H,  H ],  # A+7
    19: [S,  S,  S,  S,  DS, S,  S,  S,  S,  S ],  # A+8
    20: [S,  S,  S,  S,  S,  S,  S,  S,  S,  S ],  # A+9
}

# --- PARES ---
# Columnas: crupier 2,3,4,5,6,7,8,9,10,A
PAIRS: dict[str, list[BasicAction]] = {
    "A":  [P,  P,  P,  P,  P,  P,  P,  P,  P,  P ],
    "2":  [PH, PH, P,  P,  P,  P,  H,  H,  H,  H ],
    "3":  [PH, PH, P,  P,  P,  P,  H,  H,  H,  H ],
    "4":  [H,  H,  H,  PH, PH, H,  H,  H,  H,  H ],
    "5":  [D,  D,  D,  D,  D,  D,  D,  D,  H,  H ],  # tratar como hard 10
    "6":  [PH, P,  P,  P,  P,  H,  H,  H,  H,  H ],
    "7":  [P,  P,  P,  P,  P,  P,  H,  H,  H,  H ],
    "8":  [P,  P,  P,  P,  P,  P,  P,  P,  P,  RP],
    "9":  [P,  P,  P,  P,  P,  S,  P,  P,  S,  S ],
    "10": [S,  S,  S,  S,  S,  S,  S,  S,  S,  S ],
    "J":  [S,  S,  S,  S,  S,  S,  S,  S,  S,  S ],
    "Q":  [S,  S,  S,  S,  S,  S,  S,  S,  S,  S ],
    "K":  [S,  S,  S,  S,  S,  S,  S,  S,  S,  S ],
}

def get_basic_strategy(hand: "Hand", dealer_upcard_value: int, rules: "Rules") -> BasicAction:
    """
    Devuelve la acción óptima según la estrategia básica.

    Parámetros
    ----------
    hand               : mano actual del jugador
    dealer_upcard_value: valor numérico de la carta visible del crupier (2-11)
    rules              : reglas activas (para ajustar DAS, surrender, etc.)
    """
    col = UPCARD_INDEX.get(min(dealer_upcard_value, 10), 8)

    # --- Pares ---
    if hand.can_split:
        rank = hand.cards[0].rank
        action = PAIRS.get(rank, [H]*10)[col]
        return _resolve_action(action, hand, rules)

    # --- Soft ---
    if hand.is_soft and hand.value in SOFT:
        action = SOFT[hand.value][col]
        return _resolve_action(action, hand, rules)

    # --- Hard ---
    v = hand.value
    if v >= 18:
        return BasicAction.S
    if v <= 8:
        return BasicAction.H
    action = HARD.get(v, [H]*10)[col]
    return _resolve_action(action, hand, rules)


def _resolve_action(action: BasicAction, hand: "Hand", rules: "Rules") -> BasicAction:
    """
    Ajusta la acción si ciertas opciones no están disponibles
    (p.ej. si no se puede doblar, la 'D' se convierte en H o S).
    """
    from core.rules import SurrenderRule, DoubleRule

    match action:
        case BasicAction.D:
            if not hand.can_double:
                return BasicAction.H
        case BasicAction.DS:
            if not hand.can_double:
                return BasicAction.S
        case BasicAction.P | BasicAction.PH:
            if not hand.can_split:
                return BasicAction.H
        case BasicAction.RP:
            if rules.surrender_rule == SurrenderRule.NONE:
                return BasicAction.P if hand.can_split else BasicAction.H
        case BasicAction.R:
            if rules.surrender_rule == SurrenderRule.NONE:
                return BasicAction.H
        case BasicAction.RS:
            if rules.surrender_rule == SurrenderRule.NONE:
                return BasicAction.S

    return action


# ------------------------------------------------------------------
# Clasificación por color para la UI (hint display)
# ------------------------------------------------------------------
ACTION_COLOR: dict[BasicAction, str] = {
    BasicAction.H:  "#E74C3C",   # rojo   → Hit
    BasicAction.S:  "#27AE60",   # verde  → Stand
    BasicAction.D:  "#F39C12",   # naranja → Double
    BasicAction.DS: "#E67E22",
    BasicAction.P:  "#2980B9",   # azul   → Split
    BasicAction.PH: "#5DADE2",
    BasicAction.R:  "#8E44AD",   # morado → Surrender
    BasicAction.RS: "#9B59B6",
    BasicAction.RP: "#A569BD",
}