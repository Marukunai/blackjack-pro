# engine/challenges.py
# Fase 25: modo Desafío -- objetivos concretos con un límite de manos,
# jugados en solitario sobre el mismo GameEngine de siempre (no es un
# modo de juego aparte: es una sesión normal con reglas/fichas propias y
# una condición de victoria/derrota que se comprueba tras cada ronda).
# -------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Literal, TYPE_CHECKING

from core.rules import Rules
from config import i18n

if TYPE_CHECKING:
    from core.player import SessionStats

Status = Literal["in_progress", "won", "lost"]


@dataclass
class Challenge:
    """
    Un desafío define su propia partida (fichas iniciales, límites de
    apuesta) y una condición de fin evaluada tras cada ronda -- se
    reutilizan `SessionStats` y `GameEngine` tal cual, sin lógica de
    motor nueva. Cada desafío usa como mucho UNA de estas condiciones de
    objetivo (las demás quedan a None):

    - `target_chips`  : llegar a esta cantidad de fichas.
    - `target_streak` : llegar a esta racha de victorias seguidas.
    - `require_profit`: terminar el límite de manos con más fichas de
      las que se empezó (sin objetivo intermedio, solo al final).
    - (ninguna de las tres): sobrevivir sin quebrar hasta el límite de
      manos ya es en sí mismo el objetivo (p. ej. "Superviviente").

    `fail_on_any_loss` -- además de lo anterior, cualquier derrota/pasada
    /rendición termina el desafío al instante (usado por los desafíos de
    racha "sin fallos": no basta con llegar a la racha, hay que hacerlo
    sin tropezar ni una vez).
    """
    id: str
    name: str
    description: str
    icon: str            # letra de palo (ver ui.icons.draw_suit) para el icono
    color: tuple
    hand_limit: int
    starting_chips: float
    min_bet: float
    max_bet: float
    num_decks: int = 4
    target_chips: Optional[float] = None
    target_streak: Optional[int] = None
    require_profit: bool = False
    fail_on_any_loss: bool = False

    # ------------------------------------------------------------------
    def build_rules(self) -> Rules:
        """Reglas estándar (Vegas Strip-like) con las fichas/límites del
        desafío -- los desafíos no tocan las reglas de la mesa en sí,
        solo el dinero en juego y el objetivo."""
        return Rules(
            num_decks=self.num_decks,
            penetration=0.75,
            min_bet=self.min_bet,
            max_bet=self.max_bet,
            starting_chips=self.starting_chips,
        )

    # ------------------------------------------------------------------
    def evaluate(self, stats: "SessionStats", chips: float) -> Status:
        """Se llama tras CADA ronda resuelta (con `stats`/`chips` ya
        actualizados). Devuelve 'in_progress' mientras el desafío sigue
        abierto, o el resultado final en cuanto se decide."""
        if self.fail_on_any_loss and stats.hand_log:
            last_tag, _streak = stats.hand_log[-1]
            if last_tag in ("loss", "bust", "surrender"):
                return "lost"

        if self.target_streak is not None and stats.current_streak >= self.target_streak:
            return "won"

        if self.target_chips is not None and chips >= self.target_chips:
            return "won"

        if stats.hands_played >= self.hand_limit:
            if self.require_profit:
                return "won" if chips > self.starting_chips else "lost"
            if self.target_chips is not None or self.target_streak is not None:
                return "lost"   # se acabaron las manos sin llegar al objetivo
            return "won"        # objetivo era sobrevivir hasta aquí -- lo logró

        return "in_progress"

    # ------------------------------------------------------------------
    def progress(self, stats: "SessionStats", chips: float) -> float:
        """0.0-1.0, para la barra de progreso de la UI."""
        if self.target_chips is not None:
            span = self.target_chips - self.starting_chips
            if span <= 0:
                return 1.0
            return max(0.0, min(1.0, (chips - self.starting_chips) / span))
        if self.target_streak is not None:
            return max(0.0, min(1.0, stats.current_streak / self.target_streak))
        return max(0.0, min(1.0, stats.hands_played / self.hand_limit))

    def progress_label(self, stats: "SessionStats", chips: float) -> str:
        if self.target_chips is not None:
            return i18n.t("challenge.progress_chips", chips=int(chips), target=int(self.target_chips))
        if self.target_streak is not None:
            cur = max(0, stats.current_streak)
            return i18n.t("challenge.progress_streak", cur=cur, target=self.target_streak)
        if self.require_profit:
            return i18n.t("challenge.progress_net", net=chips - self.starting_chips)
        return i18n.t("challenge.progress_hand", hand=stats.hands_played, limit=self.hand_limit)


# ----------------------------------------------------------------------
# Catálogo (como engine/achievements.py: se puede ampliar más adelante
# sin tocar nada de lo que ya funciona -- ver ui/challenge_select.py y
# el manejo en ui/renderer.py, ninguno de los dos depende de cuántos
# desafíos haya).
# ----------------------------------------------------------------------
CHALLENGES: list[Challenge] = [
    Challenge(
        id="meta_rapida",
        name="Meta Rápida",
        description="Llega a $1500 en fichas antes de que se acaben 20 manos.",
        icon="D", color=(80, 200, 220),
        hand_limit=20, starting_chips=1000.0, min_bet=25.0, max_bet=500.0,
        target_chips=1500.0,
    ),
    Challenge(
        id="superviviente",
        name="Superviviente",
        description="Juega 25 manos seguidas sin quedarte sin fichas. Empiezas "
                     "corto de dinero -- cuidado con las apuestas.",
        icon="C", color=(120, 200, 120),
        hand_limit=25, starting_chips=300.0, min_bet=25.0, max_bet=100.0,
    ),
    Challenge(
        id="racha_hierro",
        name="Racha de Hierro",
        description="Consigue 5 victorias seguidas sin perder ni una sola mano "
                     "por el camino. Un solo tropiezo y se acaba.",
        icon="S", color=(210, 210, 210),
        hand_limit=30, starting_chips=1000.0, min_bet=10.0, max_bet=500.0,
        target_streak=5, fail_on_any_loss=True,
    ),
    Challenge(
        id="contrarreloj",
        name="Contrarreloj",
        description="Termina exactamente 15 manos con más fichas de las que "
                     "empezaste.",
        icon="H", color=(220, 100, 130),
        hand_limit=15, starting_chips=1000.0, min_bet=25.0, max_bet=500.0,
        require_profit=True,
    ),
]

_BY_ID = {c.id: c for c in CHALLENGES}


def get_challenge(challenge_id: str) -> Challenge:
    return _BY_ID[challenge_id]
