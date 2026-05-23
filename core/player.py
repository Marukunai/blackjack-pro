# core/player.py
# Clase Player: fichas, manos activas, historial de sesión.
# -------------------------------------------------------------
from __future__ import annotations

from typing import Optional
from core.hand import Hand


class Player:
    """
    Representa al jugador humano.

    Gestiona su saldo, las manos activas en la ronda actual
    y las estadísticas acumuladas de la sesión.
    """

    def __init__(self, name: str = "Player", chips: float = 1000.0) -> None:
        self.name = name
        self.chips = chips

        # Manos de la ronda actual (puede haber varias tras splits)
        self.hands: list[Hand] = []
        self.active_hand_index: int = 0    # índice de la mano en juego

        # Apuesta de seguro (side bet)
        self.insurance_bet: float = 0.0

        # Estadísticas de sesión
        self.stats = SessionStats()

    # ------------------------------------------------------------------
    # Gestión de manos
    # ------------------------------------------------------------------
    def new_round(self, bet: float) -> Hand:
        """Limpia las manos anteriores y crea la mano inicial de la ronda."""
        self.hands.clear()
        self.active_hand_index = 0
        self.insurance_bet = 0.0
        hand = Hand(bet=bet)
        self.hands.append(hand)
        return hand

    @property
    def active_hand(self) -> Optional[Hand]:
        if 0 <= self.active_hand_index < len(self.hands):
            return self.hands[self.active_hand_index]
        return None

    def advance_hand(self) -> bool:
        """
        Avanza al siguiente split de mano.
        Devuelve True si queda mano activa, False si se han jugado todas.
        """
        self.active_hand_index += 1
        return self.active_hand_index < len(self.hands)

    def all_hands_finished(self) -> bool:
        return all(h.is_finished for h in self.hands)

    # ------------------------------------------------------------------
    # Fichas
    # ------------------------------------------------------------------
    def place_bet(self, amount: float) -> None:
        if amount > self.chips:
            raise ValueError(f"No tienes suficientes fichas (tienes {self.chips:.0f}).")
        self.chips -= amount

    def receive(self, amount: float) -> None:
        """Añade fichas al saldo (ganancias + devolución de apuesta)."""
        self.chips += amount

    def can_afford(self, amount: float) -> bool:
        return self.chips >= amount

    # ------------------------------------------------------------------
    # Seguro
    # ------------------------------------------------------------------
    def place_insurance(self, amount: float) -> None:
        if amount > self.chips:
            raise ValueError("No tienes fichas para el seguro.")
        self.chips -= amount
        self.insurance_bet = amount

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------
    def __str__(self) -> str:
        return f"{self.name} (chips={self.chips:.0f})"

    def __repr__(self) -> str:
        return f"Player(name={self.name!r}, chips={self.chips})"


# ------------------------------------------------------------------
# Estadísticas de sesión (objeto auxiliar)
# ------------------------------------------------------------------
class SessionStats:
    """Acumula métricas de la sesión actual."""

    def __init__(self) -> None:
        self.hands_played: int = 0
        self.hands_won: int = 0
        self.hands_lost: int = 0
        self.hands_push: int = 0
        self.hands_surrendered: int = 0
        self.blackjacks: int = 0
        self.busts: int = 0
        self.total_wagered: float = 0.0
        self.net_profit: float = 0.0
        self.peak_chips: float = 0.0
        self.lowest_chips: float = float("inf")
        self.current_streak: int = 0    # + ganando, - perdiendo
        self.best_streak: int = 0
        self.worst_streak: int = 0

    @property
    def win_rate(self) -> float:
        if self.hands_played == 0:
            return 0.0
        return self.hands_won / self.hands_played

    @property
    def roi(self) -> float:
        """Retorno sobre lo apostado (puede ser negativo)."""
        if self.total_wagered == 0:
            return 0.0
        return self.net_profit / self.total_wagered

    def record_win(self, profit: float) -> None:
        self.hands_played += 1
        self.hands_won += 1
        self.net_profit += profit
        self.current_streak = max(1, self.current_streak + 1)
        self.best_streak = max(self.best_streak, self.current_streak)

    def record_loss(self, loss: float) -> None:
        self.hands_played += 1
        self.hands_lost += 1
        self.net_profit -= loss
        self.current_streak = min(-1, self.current_streak - 1)
        self.worst_streak = min(self.worst_streak, self.current_streak)

    def record_push(self) -> None:
        self.hands_played += 1
        self.hands_push += 1
        self.current_streak = 0

    def record_surrender(self, returned: float, wagered: float) -> None:
        self.hands_played += 1
        self.hands_surrendered += 1
        self.net_profit -= (wagered - returned)
        self.current_streak = 0

    def __str__(self) -> str:
        return (
            f"Manos: {self.hands_played} | "
            f"W/L/P: {self.hands_won}/{self.hands_lost}/{self.hands_push} | "
            f"WR: {self.win_rate:.1%} | "
            f"ROI: {self.roi:+.1%} | "
            f"Neto: {self.net_profit:+.0f}"
        )