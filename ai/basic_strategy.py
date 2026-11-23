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

    # La rendición sólo es una opción legal como primerísima decisión de
    # la mano (exactamente 2 cartas, sin provenir de un split y sin
    # haberse rendido ya) -- igual que can_double/can_split ya exigen
    # len(cards) == 2. Sin esta comprobación, una mano que ya ha pedido
    # carta (p.ej. hard 15 tras un hit) podía recibir "surrender" como
    # recomendación aunque el motor ya no la ofrezca como acción válida,
    # dejando congelado para siempre a cualquiera que la ejecute a
    # ciegas (p.ej. la IA de la Fase 33).
    can_surrender = (
        len(hand.cards) == 2
        and not hand.is_split
        and not hand.surrendered
        and rules.surrender_rule != SurrenderRule.NONE
    )

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
            if not can_surrender:
                return BasicAction.P if hand.can_split else BasicAction.H
        case BasicAction.R:
            if not can_surrender:
                return BasicAction.H
        case BasicAction.RS:
            if not can_surrender:
                return BasicAction.S

    return action


# ------------------------------------------------------------------
# Fase 19 — modo entrenamiento: reduce cualquier BasicAction (incluidas
# las formas compuestas "X si no Y") a la acción de juego real que
# corresponde tomar, dado que _resolve_action ya ha comprobado que esa
# opción está disponible con la mano/reglas actuales.
# ------------------------------------------------------------------
_ACTION_TO_PLAY: dict[BasicAction, str] = {
    BasicAction.H:  "hit",
    BasicAction.S:  "stand",
    BasicAction.D:  "double",
    BasicAction.DS: "double",
    BasicAction.P:  "split",
    BasicAction.PH: "split",
    BasicAction.R:  "surrender",
    BasicAction.RS: "surrender",
    BasicAction.RP: "surrender",
}


def recommended_play(hand: "Hand", dealer_upcard_value: int, rules: "Rules") -> str:
    """Como get_basic_strategy(), pero devuelve directamente la acción de
    juego ('hit'/'stand'/'double'/'split'/'surrender') que GameEngine
    espera, ya resuelta a una opción realmente disponible."""
    action = get_basic_strategy(hand, dealer_upcard_value, rules)
    return _ACTION_TO_PLAY.get(action, "hit")


# ------------------------------------------------------------------
# Fase 38 -- "personalidades" de oponente IA: un pequeño desvío sobre la
# recomendación de estrategia básica, para que no todos los bots jueguen
# exactamente igual en una mesa con varios. Deliberadamente simple y
# conservador en el propio código: solo toca si se dobla/se separa o no
# (nunca convierte un hit/stand/surrender en otra cosa), así que el
# resultado sigue siendo una jugada razonable en cualquier caso -- y
# ui/renderer.py::_run_bot_turn valida igualmente la acción final contra
# las que el motor considera disponibles ahora mismo, como red de
# seguridad adicional (ver el bug de la "rendición fantasma" corregido
# en _resolve_action más arriba).
# ------------------------------------------------------------------
PERSONALITIES = ("perfect", "conservative", "aggressive")


def apply_personality(action: str, hand: "Hand", personality: str) -> str:
    """Ajusta `action` (ya resuelta por recommended_play) según la
    personalidad del bot:

    - "perfect": sin cambios, estrategia básica tal cual.
    - "conservative": nunca dobla ni separa -- prefiere pedir carta antes
      que arriesgar el doble de apuesta o abrir una segunda mano. "hit"
      siempre es una opción disponible mientras la mano siga en juego
      (ver engine/actions.py::available_actions), así que esta rebaja
      nunca puede toparse con una acción inválida.
    - "aggressive": dobla más de lo que recomendaría la tabla (en
      cualquier total duro de 9 a 11 en la primera decisión) y separa
      cualquier par que pueda, en vez de pedir/plantarse -- un jugador
      que se arriesga más de la cuenta, a propósito."""
    if personality == "conservative":
        if action in ("double", "split"):
            return "hit"
        return action

    if personality == "aggressive":
        is_first = len(hand.cards) == 2 and not hand.is_split
        if action in ("hit", "stand") and hand.can_split:
            return "split"
        if (action in ("hit", "stand") and is_first and hand.can_double
                and hand.is_hard and hand.value in (9, 10, 11)):
            return "double"
        return action

    return action


def recommended_play_with_personality(hand: "Hand", dealer_upcard_value: int, rules: "Rules",
                                       personality: str = "perfect") -> str:
    """Como recommended_play(), pero pasada por apply_personality() --
    lo que de verdad consulta el oponente IA (ver
    ui/renderer.py::_run_bot_turn)."""
    action = recommended_play(hand, dealer_upcard_value, rules)
    return apply_personality(action, hand, personality)


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