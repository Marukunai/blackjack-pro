# engine/statistics.py
# Estadísticas de sesión avanzadas y exportación.
# -------------------------------------------------------------
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.player import Player


class StatisticsManager:
    """
    Gestiona el guardado, carga y presentación de estadísticas.
    Trabaja sobre el objeto SessionStats del Player.
    """

    SAVE_PATH = Path("saves/profile.json")

    def __init__(self, player: "Player") -> None:
        self.player = player

    # ------------------------------------------------------------------
    # Resumen legible
    # ------------------------------------------------------------------
    def summary(self) -> str:
        s = self.player.stats
        lines = [
            f"{'─'*40}",
            f"  ESTADÍSTICAS DE SESIÓN",
            f"{'─'*40}",
            f"  Jugador       : {self.player.name}",
            f"  Fichas        : {self.player.chips:.0f}",
            f"  Manos jugadas : {s.hands_played}",
            f"  Victorias     : {s.hands_won}  ({s.win_rate:.1%})",
            f"  Derrotas      : {s.hands_lost}",
            f"  Empates       : {s.hands_push}",
            f"  Rendiciones   : {s.hands_surrendered}",
            f"  Blackjacks    : {s.blackjacks}",
            f"  Pasadas (bust): {s.busts}",
            f"  Total apostado: {s.total_wagered:.0f}",
            f"  Beneficio neto: {s.net_profit:+.0f}",
            f"  ROI           : {s.roi:+.1%}",
            f"  Mejor racha   : +{s.best_streak}",
            f"  Peor racha    : {s.worst_streak}",
            f"  Pico de fichas: {s.peak_chips:.0f}",
            f"{'─'*40}",
        ]
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Persistencia
    # ------------------------------------------------------------------
    def save(self) -> None:
        s = self.player.stats
        data = {
            "name": self.player.name,
            "chips": self.player.chips,
            "hands_played": s.hands_played,
            "hands_won": s.hands_won,
            "hands_lost": s.hands_lost,
            "hands_push": s.hands_push,
            "hands_surrendered": s.hands_surrendered,
            "blackjacks": s.blackjacks,
            "busts": s.busts,
            "total_wagered": s.total_wagered,
            "net_profit": s.net_profit,
            "peak_chips": s.peak_chips,
            "lowest_chips": s.lowest_chips if s.lowest_chips != float("inf") else 0,
            "best_streak": s.best_streak,
            "worst_streak": s.worst_streak,
        }
        self.SAVE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(self.SAVE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load(self) -> bool:
        """Carga el perfil. Devuelve True si se cargó, False si no existe."""
        if not self.SAVE_PATH.exists():
            return False
        with open(self.SAVE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        s = self.player.stats
        self.player.name = data.get("name", self.player.name)
        self.player.chips = data.get("chips", self.player.chips)
        s.hands_played     = data.get("hands_played", 0)
        s.hands_won        = data.get("hands_won", 0)
        s.hands_lost       = data.get("hands_lost", 0)
        s.hands_push       = data.get("hands_push", 0)
        s.hands_surrendered = data.get("hands_surrendered", 0)
        s.blackjacks       = data.get("blackjacks", 0)
        s.busts            = data.get("busts", 0)
        s.total_wagered    = data.get("total_wagered", 0.0)
        s.net_profit       = data.get("net_profit", 0.0)
        s.peak_chips       = data.get("peak_chips", self.player.chips)
        s.lowest_chips     = data.get("lowest_chips", self.player.chips)
        s.best_streak      = data.get("best_streak", 0)
        s.worst_streak     = data.get("worst_streak", 0)
        return True