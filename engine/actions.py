# engine/actions.py
# Todas las acciones posibles del jugador con validación de reglas.
# -------------------------------------------------------------
from __future__ import annotations

from typing import TYPE_CHECKING

from core.hand import Hand
from core.rules import Rules, SurrenderRule, DoubleRule
from engine.game_state import ActionResult

if TYPE_CHECKING:
    from core.deck import Deck
    from core.player import Player
    from core.dealer import Dealer


# ------------------------------------------------------------------
# Validación de acciones disponibles
# ------------------------------------------------------------------

def available_actions(
    hand: Hand,
    player: "Player",
    dealer: "Dealer",
    rules: Rules,
    is_first_action: bool = True,
) -> list[str]:
    """
    Devuelve la lista de acciones válidas para la mano actual.
    Posibles valores: 'hit', 'stand', 'double', 'split', 'surrender', 'insurance'
    """
    if hand.is_finished:
        return []

    actions = ["hit", "stand"]

    # Double Down
    if hand.can_double and player.can_afford(hand.bet):
        if rules.double_rule == DoubleRule.ANY_TWO:
            actions.append("double")
        elif rules.double_rule == DoubleRule.NINE_TEN_ELEVEN and hand.value in (9, 10, 11):
            actions.append("double")

    # Double After Split
    if hand.is_split and not rules.double_after_split and "double" in actions:
        actions.remove("double")

    # Split
    if (
        hand.can_split
        and player.can_afford(hand.bet)
        and len(player.hands) <= rules.max_splits
    ):
        # No re-splitear Ases si la regla lo prohíbe
        if hand.is_pair_of_aces and not rules.resplit_aces and hand.is_split:
            pass  # no se añade split
        else:
            actions.append("split")

    # Surrender (solo en la primera acción, con 2 cartas)
    if (
        is_first_action
        and len(hand.cards) == 2
        and not hand.is_split  # el late surrender generalmente no aplica en splits
        and rules.surrender_rule != SurrenderRule.NONE
    ):
        # Late surrender: no si el crupier tiene BJ (se comprueba en el engine)
        # Early surrender: siempre
        actions.append("surrender")

    return actions


# ------------------------------------------------------------------
# Acciones
# ------------------------------------------------------------------

def action_hit(hand: Hand, deck: "Deck") -> ActionResult:
    """El jugador pide carta."""
    card = deck.deal()
    hand.add_card(card)

    if hand.is_bust:
        hand.stood = True          # mano terminada
        return ActionResult.BUST
    if hand.value == 21:
        hand.stood = True
        return ActionResult.TWENTY_ONE
    return ActionResult.OK


def action_stand(hand: Hand) -> ActionResult:
    """El jugador planta."""
    hand.stood = True
    return ActionResult.STAND


def action_double(hand: Hand, deck: "Deck", player: "Player") -> ActionResult:
    """
    Double Down: dobla la apuesta, recibe exactamente 1 carta y planta.
    """
    extra = hand.bet
    player.place_bet(extra)
    hand.bet += extra
    hand.is_doubled = True

    card = deck.deal()
    hand.add_card(card)
    hand.stood = True              # solo 1 carta permitida tras doblar

    if hand.is_bust:
        return ActionResult.BUST
    if hand.value == 21:
        return ActionResult.TWENTY_ONE
    return ActionResult.STAND


def action_split(hand: Hand, deck: "Deck", player: "Player", rules: Rules) -> tuple[Hand, Hand]:
    """
    Split: divide la mano en 2, cada una con 1 carta y la misma apuesta.
    Devuelve las dos nuevas manos.
    """
    card1 = hand.cards[0]
    card2 = hand.cards[1]

    player.place_bet(hand.bet)     # se duplica la apuesta

    hand1 = Hand(bet=hand.bet)
    hand1.is_split = True
    hand1.add_card(card1)
    hand1.add_card(deck.deal())

    hand2 = Hand(bet=hand.bet)
    hand2.is_split = True
    hand2.add_card(card2)
    hand2.add_card(deck.deal())

    # Si son Ases spliteados y la regla no permite hit → plantan automáticamente
    if card1.is_ace and not rules.hit_split_aces:
        hand1.stood = True
        hand2.stood = True

    return hand1, hand2


def action_surrender(hand: Hand, rules: Rules) -> ActionResult:
    """
    Surrender: el jugador se rinde y recupera la mitad de la apuesta.
    La devolución real se gestiona en payout.py.
    """
    hand.surrendered = True
    hand.stood = True
    return ActionResult.SURRENDER


def action_insurance(player: "Player", dealer: "Dealer", rules: Rules) -> bool:
    """
    Ofrece seguro cuando el crupier muestra un As.
    La apuesta de seguro es hasta la mitad de la apuesta original.
    Devuelve True si el jugador puede y decide asegurar.
    (La UI decide si el jugador acepta; aquí solo validamos y cobramos.)
    """
    if not dealer.showing_ace or not rules.insurance_allowed:
        return False

    max_insurance = player.active_hand.bet / 2
    if not player.can_afford(max_insurance):
        return False

    player.place_insurance(max_insurance)
    return True


def action_even_money(player: "Player", dealer: "Dealer", rules: Rules) -> bool:
    """
    Even Money: si el jugador tiene BJ y el crupier muestra As,
    puede cobrar 1:1 inmediatamente en lugar de arriesgarse al push.
    Solo disponible si las reglas lo permiten.
    """
    hand = player.active_hand
    if hand is None:
        return False
    return (
        rules.even_money_allowed
        and dealer.showing_ace
        and hand.is_blackjack
    )