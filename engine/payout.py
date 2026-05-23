# engine/payout.py
# Resolución de manos y cálculo de pagos.
# -------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from core.hand import Hand
from core.rules import Rules
from engine.game_state import RoundResult

if TYPE_CHECKING:
    from core.player import Player
    from core.dealer import Dealer


@dataclass
class HandPayout:
    """Resultado y pago de una mano individual."""
    hand: Hand
    result: RoundResult
    net: float          # ganancia neta (negativa si se pierde)
    returned: float     # fichas devueltas al jugador (apuesta + ganancias)


def resolve_hand(
    hand: Hand,
    dealer: "Dealer",
    rules: Rules,
) -> HandPayout:
    """
    Compara una mano de jugador contra el crupier y devuelve el pago.
    """
    bet = hand.bet

    # --- Surrender ---
    if hand.surrendered:
        returned = rules.surrender_return(bet)
        return HandPayout(hand, RoundResult.SURRENDER, net=-(bet - returned), returned=returned)

    # --- Bust del jugador → pierde siempre ---
    if hand.is_bust:
        return HandPayout(hand, RoundResult.LOSS, net=-bet, returned=0.0)

    dealer_val = dealer.value
    player_val = hand.value

    # --- Blackjack natural del jugador ---
    if hand.is_blackjack:
        if dealer.has_blackjack:
            # Push (empate entre dos naturales)
            return HandPayout(hand, RoundResult.PUSH, net=0.0, returned=bet)
        win = rules.blackjack_win(bet)
        return HandPayout(hand, RoundResult.BLACKJACK_WIN, net=win, returned=bet + win)

    # --- Bust del crupier → jugador gana (si no está bust él) ---
    if dealer.is_bust:
        return HandPayout(hand, RoundResult.DEALER_BUST, net=bet, returned=bet * 2)

    # --- Blackjack del crupier (jugador no tiene BJ) → pierde ---
    if dealer.has_blackjack:
        # Con OBBO: si el jugador dobló o spliteó, pierde toda la apuesta
        return HandPayout(hand, RoundResult.LOSS, net=-bet, returned=0.0)

    # --- Comparación de valores ---
    if player_val > dealer_val:
        return HandPayout(hand, RoundResult.WIN, net=bet, returned=bet * 2)
    elif player_val < dealer_val:
        return HandPayout(hand, RoundResult.LOSS, net=-bet, returned=0.0)
    else:
        return HandPayout(hand, RoundResult.PUSH, net=0.0, returned=bet)


def resolve_insurance(player: "Player", dealer: "Dealer", rules: Rules) -> float:
    """
    Resuelve la apuesta de seguro.
    Devuelve la cantidad neta que recibe el jugador (puede ser negativa).
    """
    if player.insurance_bet == 0:
        return 0.0

    side_bet = player.insurance_bet

    if dealer.has_blackjack:
        win = rules.insurance_win(side_bet)
        player.receive(side_bet + win)   # devuelve apuesta + ganancias
        return win
    else:
        # Pierde el seguro
        return -side_bet


def apply_payouts(
    player: "Player",
    dealer: "Dealer",
    rules: Rules,
) -> list[HandPayout]:
    """
    Resuelve todas las manos del jugador, actualiza sus fichas
    y registra las estadísticas.

    Devuelve la lista de HandPayout para que la UI lo muestre.
    """
    results: list[HandPayout] = []

    for hand in player.hands:
        payout = resolve_hand(hand, dealer, rules)
        player.receive(payout.returned)
        results.append(payout)

        # Actualizar estadísticas
        stats = player.stats
        stats.total_wagered += hand.bet

        match payout.result:
            case RoundResult.WIN | RoundResult.BLACKJACK_WIN | RoundResult.DEALER_BUST:
                stats.record_win(payout.net)
                if payout.result == RoundResult.BLACKJACK_WIN:
                    stats.blackjacks += 1
            case RoundResult.LOSS:
                stats.record_loss(abs(payout.net))
                if hand.is_bust:
                    stats.busts += 1
            case RoundResult.PUSH:
                stats.record_push()
            case RoundResult.SURRENDER:
                stats.record_surrender(payout.returned, hand.bet)

    # Seguro
    resolve_insurance(player, dealer, rules)

    # Actualizar pico / valle de fichas
    player.stats.peak_chips = max(player.stats.peak_chips, player.chips)
    player.stats.lowest_chips = min(player.stats.lowest_chips, player.chips)

    return results