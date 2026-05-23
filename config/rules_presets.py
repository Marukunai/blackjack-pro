# config/rules_presets.py
# Presets de reglas de casino reales.
# -------------------------------------------------------------
from core.rules import (
    Rules, BlackjackPayout, DealerRule,
    SurrenderRule, DoubleRule,
)


def vegas_strip() -> Rules:
    """
    Vegas Strip (reglas más comunes en Las Vegas Strip).
    6 mazos, S17, BJ 3:2, DAS, Late Surrender.
    """
    return Rules(
        num_decks=6,
        penetration=0.75,
        dealer_rule=DealerRule.STAND_SOFT_17,
        blackjack_payout=BlackjackPayout.THREE_TO_TWO,
        double_rule=DoubleRule.ANY_TWO,
        double_after_split=True,
        max_splits=3,
        resplit_aces=False,
        hit_split_aces=False,
        surrender_rule=SurrenderRule.LATE,
        insurance_allowed=True,
        even_money_allowed=True,
        min_bet=10.0,
        max_bet=1000.0,
    )


def atlantic_city() -> Rules:
    """
    Atlantic City (regulación de New Jersey).
    8 mazos, S17, BJ 3:2, DAS, Late Surrender.
    """
    return Rules(
        num_decks=8,
        penetration=0.75,
        dealer_rule=DealerRule.STAND_SOFT_17,
        blackjack_payout=BlackjackPayout.THREE_TO_TWO,
        double_rule=DoubleRule.ANY_TWO,
        double_after_split=True,
        max_splits=3,
        resplit_aces=False,
        hit_split_aces=False,
        surrender_rule=SurrenderRule.LATE,
        insurance_allowed=True,
        even_money_allowed=True,
        min_bet=10.0,
        max_bet=2000.0,
    )


def european() -> Rules:
    """
    European Blackjack.
    2 mazos, S17, BJ 3:2, sin hole card (ENHC), sin Surrender.
    """
    return Rules(
        num_decks=2,
        penetration=0.75,
        dealer_rule=DealerRule.STAND_SOFT_17,
        blackjack_payout=BlackjackPayout.THREE_TO_TWO,
        double_rule=DoubleRule.NINE_TEN_ELEVEN,
        double_after_split=False,
        max_splits=1,
        resplit_aces=False,
        hit_split_aces=False,
        surrender_rule=SurrenderRule.NONE,
        insurance_allowed=False,
        even_money_allowed=False,
        min_bet=5.0,
        max_bet=500.0,
        original_bets_only=True,
    )


def single_deck() -> Rules:
    """
    Single Deck (reglas clásicas de 1 mazo).
    1 mazo, H17, BJ 6:5 (común en casinos modernos), sin DAS.
    """
    return Rules(
        num_decks=1,
        penetration=0.65,
        dealer_rule=DealerRule.HIT_SOFT_17,
        blackjack_payout=BlackjackPayout.SIX_TO_FIVE,
        double_rule=DoubleRule.ANY_TWO,
        double_after_split=False,
        max_splits=1,
        resplit_aces=False,
        hit_split_aces=False,
        surrender_rule=SurrenderRule.NONE,
        insurance_allowed=True,
        even_money_allowed=True,
        min_bet=5.0,
        max_bet=300.0,
    )


def downtown_vegas() -> Rules:
    """
    Downtown Vegas (Fremont Street).
    2 mazos, H17, BJ 3:2, DAS, no Surrender.
    """
    return Rules(
        num_decks=2,
        penetration=0.70,
        dealer_rule=DealerRule.HIT_SOFT_17,
        blackjack_payout=BlackjackPayout.THREE_TO_TWO,
        double_rule=DoubleRule.ANY_TWO,
        double_after_split=True,
        max_splits=3,
        resplit_aces=False,
        hit_split_aces=False,
        surrender_rule=SurrenderRule.NONE,
        insurance_allowed=True,
        even_money_allowed=True,
        min_bet=5.0,
        max_bet=500.0,
    )


# Mapa de nombre → función para el menú de configuración
PRESETS: dict[str, callable] = {
    "Vegas Strip":    vegas_strip,
    "Atlantic City":  atlantic_city,
    "European":       european,
    "Single Deck":    single_deck,
    "Downtown Vegas": downtown_vegas,
}


def get_preset(name: str) -> Rules:
    """Devuelve un objeto Rules para el preset dado."""
    fn = PRESETS.get(name)
    if fn is None:
        raise ValueError(f"Preset desconocido: {name!r}. Opciones: {list(PRESETS)}")
    return fn()