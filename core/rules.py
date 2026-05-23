# core/rules.py
# Dataclass Rules: todas las reglas configurables de la partida.
# -------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Literal


class BlackjackPayout(Enum):
    THREE_TO_TWO = "3:2"   # pago estándar
    SIX_TO_FIVE  = "6:5"   # peor para el jugador
    ONE_TO_ONE   = "1:1"   # pago par (peor aún)


class DealerRule(Enum):
    STAND_SOFT_17 = "S17"  # el crupier planta en soft 17 (mejor para jugador)
    HIT_SOFT_17   = "H17"  # el crupier pide en soft 17


class SurrenderRule(Enum):
    NONE  = "none"    # no se permite rendirse
    LATE  = "late"    # surrender solo si el crupier no tiene BJ (lo más común)
    EARLY = "early"   # surrender antes de que el crupier compruebe BJ (raro)


class DoubleRule(Enum):
    ANY_TWO   = "any"        # se puede doblar con cualquier 2 cartas
    NINE_TEN_ELEVEN = "9-11" # solo con 9, 10 u 11


@dataclass
class Rules:
    """
    Encapsula todas las reglas configurables de una partida de Blackjack.
    Cada preset de casino crea una instancia con sus valores específicos.
    """

    # --- Zapato ---
    num_decks: int = 6                          # 1 | 2 | 4 | 6 | 8
    penetration: float = 0.75                  # fracción repartida antes de rebarajar

    # --- Crupier ---
    dealer_rule: DealerRule = DealerRule.STAND_SOFT_17

    # --- Pagos ---
    blackjack_payout: BlackjackPayout = BlackjackPayout.THREE_TO_TWO

    # --- Double Down ---
    double_rule: DoubleRule = DoubleRule.ANY_TWO
    double_after_split: bool = True            # DAS

    # --- Split ---
    max_splits: int = 3                        # hasta 4 manos (3 splits)
    resplit_aces: bool = False                 # ¿se pueden re-splitear Ases?
    hit_split_aces: bool = False               # ¿se puede pedir tras splitear Ases?

    # --- Surrender ---
    surrender_rule: SurrenderRule = SurrenderRule.LATE

    # --- Seguro / Even Money ---
    insurance_allowed: bool = True
    even_money_allowed: bool = True

    # --- Apuestas ---
    min_bet: float = 5.0
    max_bet: float = 500.0
    starting_chips: float = 1000.0

    # --- Avanzado ---
    five_card_charlie: bool = False    # 5 cartas sin pasarse = win automático (regla opcional)
    original_bets_only: bool = False   # OBBO: en caso de BJ del crupier, se pierde solo la apuesta original

    # ------------------------------------------------------------------
    # Helpers de cálculo de pago
    # ------------------------------------------------------------------
    def blackjack_win(self, bet: float) -> float:
        """Beneficio neto de un Blackjack natural (sin contar la apuesta devuelta)."""
        match self.blackjack_payout:
            case BlackjackPayout.THREE_TO_TWO:
                return bet * 1.5
            case BlackjackPayout.SIX_TO_FIVE:
                return bet * 1.2
            case BlackjackPayout.ONE_TO_ONE:
                return bet * 1.0

    def insurance_win(self, side_bet: float) -> float:
        """El seguro paga 2:1."""
        return side_bet * 2.0

    def surrender_return(self, bet: float) -> float:
        """El surrender devuelve la mitad de la apuesta."""
        return bet * 0.5

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------
    def __str__(self) -> str:
        return (
            f"Rules({self.num_decks}D | {self.dealer_rule.value} | "
            f"BJ={self.blackjack_payout.value} | "
            f"Surrender={self.surrender_rule.value} | "
            f"DAS={self.double_after_split})"
        )