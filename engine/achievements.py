# engine/achievements.py
# Catálogo de logros y comprobación de desbloqueo por perfil.
#
# Cada logro es una condición pura sobre las estadísticas acumuladas del
# perfil (SessionStats) y el estado actual del jugador — se comprueban
# todos tras cada ronda (GameEngine._end_round) y los recién desbloqueados
# se persisten en saves/profiles.db (tabla `achievements`, ver
# engine/profile_store.py) y se notifican a la UI vía el evento
# "on_achievements_unlocked".
# -------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from core.player import Player, SessionStats
    from engine.profile_store import ProfileStore


@dataclass(frozen=True)
class Achievement:
    id: str
    name: str
    description: str
    icon: str            # forma reutilizada de ui/icons.py: "S"/"H"/"D"/"C"/"star"/"coin"
    color: tuple
    check: Callable[["SessionStats", "Player"], bool]


def _comeback(stats: "SessionStats", player: "Player") -> bool:
    """Cayó a un 15% (o menos) de su pico de fichas y se recuperó a más
    de la mitad de ese pico. Relativo al propio pico del jugador (no a
    una cifra fija) para que funcione igual con cualquier preset/apuesta
    inicial."""
    if stats.peak_chips <= 0 or stats.lowest_chips <= 0:
        return False
    return (
        stats.lowest_chips <= stats.peak_chips * 0.15
        and player.chips >= stats.peak_chips * 0.5
    )


ACHIEVEMENTS: list[Achievement] = [
    Achievement("first_win", "Primera victoria", "Gana tu primera mano.",
                "star", (80, 220, 80), lambda s, p: s.hands_won >= 1),
    Achievement("streak_5", "En racha", "Encadena 5 victorias seguidas.",
                "star", (212, 175, 55), lambda s, p: s.best_streak >= 5),
    Achievement("streak_10", "Imparable", "Encadena 10 victorias seguidas.",
                "star", (255, 215, 0), lambda s, p: s.best_streak >= 10),
    Achievement("first_bj", "¡Blackjack!", "Consigue tu primer Blackjack natural.",
                "coin", (255, 215, 0), lambda s, p: s.blackjacks >= 1),
    Achievement("bj_10", "As de la casa", "Consigue 10 Blackjacks.",
                "coin", (212, 175, 55), lambda s, p: s.blackjacks >= 10),
    Achievement("hands_100", "Cien manos", "Juega 100 manos.",
                "H", (210, 70, 70), lambda s, p: s.hands_played >= 100),
    Achievement("hands_1000", "Mil manos", "Juega 1000 manos.",
                "H", (230, 90, 90), lambda s, p: s.hands_played >= 1000),
    Achievement("high_roller", "Alto postor", "Alcanza 5000 fichas.",
                "D", (100, 170, 230), lambda s, p: s.peak_chips >= 5000),
    Achievement("whale", "Ballena", "Alcanza 10000 fichas.",
                "D", (80, 140, 220), lambda s, p: s.peak_chips >= 10000),
    Achievement("comeback", "Remontada", "Recupérate tras caer casi a la ruina.",
                "S", (220, 60, 60), _comeback),
    Achievement("first_split", "Divide y vencerás", "Haz tu primer split.",
                "C", (50, 120, 220), lambda s, p: s.hands_split >= 1),
    Achievement("split_master", "Especialista en splits", "Haz 10 splits.",
                "C", (70, 130, 240), lambda s, p: s.hands_split >= 10),
    Achievement("iron_stomach", "Estómago de hierro", "Pásate (bust) 25 veces.",
                "star", (150, 60, 60), lambda s, p: s.busts >= 25),

    # --- Fase 14: ampliación del catálogo ---
    Achievement("hands_500", "Habitual", "Juega 500 manos.",
                "H", (220, 100, 100), lambda s, p: s.hands_played >= 500),
    Achievement("streak_15", "Racha de leyenda", "Encadena 15 victorias seguidas.",
                "star", (255, 225, 120), lambda s, p: s.best_streak >= 15),
    Achievement("bj_25", "Rey del Blackjack", "Consigue 25 Blackjacks.",
                "coin", (255, 225, 90), lambda s, p: s.blackjacks >= 25),
    Achievement("busts_50", "A prueba de balas", "Pásate (bust) 50 veces.",
                "star", (170, 70, 70), lambda s, p: s.busts >= 50),
    Achievement("first_surrender", "Retirada táctica", "Ríndete por primera vez.",
                "D", (150, 150, 150), lambda s, p: s.hands_surrendered >= 1),
    Achievement("first_push", "Tablas", "Empata con el crupier por primera vez.",
                "C", (180, 180, 100), lambda s, p: s.hands_push >= 1),
    Achievement("magnate", "Magnate", "Alcanza 25000 fichas.",
                "D", (70, 120, 200), lambda s, p: s.peak_chips >= 25000),
    Achievement("profitable", "Cuentas claras", "Termina en positivo tras al menos 50 manos.",
                "coin", (100, 200, 140), lambda s, p: s.hands_played >= 50 and s.net_profit > 0),
]

BY_ID: dict[str, Achievement] = {a.id: a for a in ACHIEVEMENTS}


def check_and_unlock(player: "Player", profile_id, store: "ProfileStore") -> list[Achievement]:
    """Comprueba todos los logros aún no desbloqueados para este perfil y
    persiste los que se cumplan. Devuelve solo los que se acaban de
    desbloquear en esta llamada (para que la UI muestre el toast una
    única vez)."""
    if profile_id is None:
        return []
    already = store.get_unlocked_achievement_ids(profile_id)
    newly: list[Achievement] = []
    for ach in ACHIEVEMENTS:
        if ach.id in already:
            continue
        try:
            earned = ach.check(player.stats, player)
        except Exception:
            continue
        if earned and store.unlock_achievement(profile_id, ach.id):
            newly.append(ach)
    return newly
