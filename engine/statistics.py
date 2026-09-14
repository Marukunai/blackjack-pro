# engine/statistics.py
# Estadísticas de sesión y persistencia del perfil activo.
#
# El resumen acumulado (fichas, W/L/P, rachas...) vive en la tabla
# `profiles` de saves/profiles.db, una fila por perfil local. Además,
# cada mano jugada se registra en `hand_history` — un historial completo
# que no se pierde ni se sobrescribe en cada partida, a diferencia del
# antiguo saves/profile.json de un único perfil.
# -------------------------------------------------------------
from __future__ import annotations

import json
from typing import Optional, TYPE_CHECKING

from engine.profile_store import get_store

if TYPE_CHECKING:
    from core.player import Player
    from core.dealer import Dealer
    from engine.payout import HandPayout


class StatisticsManager:
    """
    Gestiona el guardado, carga y presentación de estadísticas del perfil
    activo. Trabaja sobre el objeto SessionStats del Player y sobre la
    fila de `profiles` identificada por `profile_id`.
    """

    def __init__(self, player: "Player", profile_id: Optional[int] = None) -> None:
        self.player = player
        self.profile_id = profile_id
        self.preset_name: str = ""

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
    # Persistencia del resumen acumulado
    # ------------------------------------------------------------------
    def save(self) -> None:
        """Guarda fichas y estadísticas acumuladas en el perfil activo.
        Sin perfil seleccionado (p. ej. modo consola sin perfiles) no hace
        nada — no hay dónde persistir."""
        if self.profile_id is None:
            return
        s = self.player.stats
        get_store().save_stats(self.profile_id, {
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
            "lowest_chips": (s.lowest_chips if s.lowest_chips != float("inf")
                             else s.peak_chips),
            "best_streak": s.best_streak,
            "worst_streak": s.worst_streak,
            "hands_split": s.hands_split,
        })

    def load(self) -> bool:
        """Carga el perfil activo. Devuelve True si se cargó, False si no
        hay perfil seleccionado o no existe en la base de datos."""
        if self.profile_id is None:
            return False
        data = get_store().get_profile(self.profile_id)
        if data is None:
            return False
        s = self.player.stats
        self.player.name  = data.get("name", self.player.name)
        self.player.chips = data.get("chips", self.player.chips)
        s.hands_played      = data.get("hands_played", 0)
        s.hands_won         = data.get("hands_won", 0)
        s.hands_lost        = data.get("hands_lost", 0)
        s.hands_push        = data.get("hands_push", 0)
        s.hands_surrendered = data.get("hands_surrendered", 0)
        s.blackjacks        = data.get("blackjacks", 0)
        s.busts             = data.get("busts", 0)
        s.total_wagered     = data.get("total_wagered", 0.0)
        s.net_profit        = data.get("net_profit", 0.0)
        s.peak_chips        = data.get("peak_chips", self.player.chips)
        s.lowest_chips      = data.get("lowest_chips", self.player.chips)
        s.best_streak       = data.get("best_streak", 0)
        s.worst_streak      = data.get("worst_streak", 0)
        s.hands_split       = data.get("hands_split", 0)
        return True

    # ------------------------------------------------------------------
    # Historial de manos — se añade, nunca se sobrescribe
    # ------------------------------------------------------------------
    def log_round(self, payouts: list["HandPayout"], dealer: Optional["Dealer"] = None) -> None:
        if self.profile_id is None:
            return
        store = get_store()

        # Fase 20: si se indica el crupier, se guardan también las cartas
        # de cada mano (jugador + crupier) como JSON, para poder repetir
        # visualmente esa mano más tarde desde HandHistoryScreen -- ver
        # ui/hand_replay.py. Sin crupier (o si algo falla al serializar)
        # se guarda igualmente la fila, solo que sin repetición posible.
        dealer_cards = None
        if dealer is not None:
            try:
                dealer_cards = [{"rank": c.rank, "suit": c.suit} for c in dealer.hand.cards]
            except Exception:
                dealer_cards = None

        for p in payouts:
            replay_data = None
            if dealer_cards is not None:
                try:
                    replay_data = json.dumps({
                        "player_cards": [{"rank": c.rank, "suit": c.suit} for c in p.hand.cards],
                        "dealer_cards": dealer_cards,
                        "is_split": p.hand.is_split,
                        "is_doubled": p.hand.is_doubled,
                        "surrendered": p.hand.surrendered,
                    })
                except Exception:
                    replay_data = None

            store.log_hand(
                self.profile_id,
                preset_name=self.preset_name,
                bet=p.hand.bet,
                result=p.result.name,
                net=p.net,
                chips_after=self.player.chips,
                replay_data=replay_data,
            )
