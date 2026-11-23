# engine/tournament.py
# Fase 39: modo Torneo -- como un Desafío (engine/challenges.py) pero
# pensado para mesa multijugador: TODOS los asientos ya sentados
# (humanos + bots, los que se eligieron en la pantalla de "¿Quién
# juega?" de siempre) arrancan con el mismo dinero y juegan el mismo
# número fijo de manos, y al llegar al límite se clasifican por fichas
# -- a diferencia de un Desafío, un Torneo no tiene condición de
# victoria/derrota propia que evaluar tras cada ronda: el límite de
# manos ES el final, y "ganar" es terminar primero en la clasificación
# final (algo que decide la UI al construir el ranking, no este objeto).
#
# Se reutiliza GameEngine/multijugador tal cual (sin lógica de motor
# nueva): un Torneo solo aporta sus propias fichas iniciales/límites de
# apuesta/mazos y el número de manos, igual que Challenge.build_rules().
# -------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass

from core.rules import Rules


@dataclass
class Tournament:
    """Define una sesión de Torneo: dinero inicial y límites de apuesta
    iguales para todos los asientos, y el número fijo de manos que se
    juegan antes de clasificar. Ver ui/tournament_select.py (catálogo) y
    ui/renderer.py (quien de verdad arranca la partida y calcula el
    ranking final cuando se alcanza hand_limit)."""
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

    # ------------------------------------------------------------------
    def build_rules(self) -> Rules:
        """Mismo patrón que Challenge.build_rules(): reglas estándar
        (Vegas Strip-like) con el dinero/límites propios del torneo -- un
        Torneo no toca las reglas de la mesa en sí, solo el dinero en
        juego y cuántas manos dura."""
        return Rules(
            num_decks=self.num_decks,
            penetration=0.75,
            min_bet=self.min_bet,
            max_bet=self.max_bet,
            starting_chips=self.starting_chips,
        )


# ----------------------------------------------------------------------
# Catálogo (mismo patrón que engine/challenges.py::CHALLENGES: se puede
# ampliar más adelante sin tocar nada de lo que ya funciona).
# ----------------------------------------------------------------------
TOURNAMENTS: list[Tournament] = [
    Tournament(
        id="torneo_rapido",
        name="Torneo Rápido",
        description="10 manos, las mismas fichas para todos los asientos. "
                     "Quien más fichas tenga al final se lleva el título.",
        icon="D", color=(80, 200, 220),
        hand_limit=10, starting_chips=1000.0, min_bet=25.0, max_bet=500.0,
    ),
    Tournament(
        id="torneo_estandar",
        name="Torneo Estándar",
        description="20 manos a mesa completa. Una partida larga de verdad "
                     "para que la clasificación final signifique algo.",
        icon="S", color=(212, 175, 55),
        hand_limit=20, starting_chips=1000.0, min_bet=25.0, max_bet=500.0,
    ),
    Tournament(
        id="torneo_maraton",
        name="Torneo Maratón",
        description="40 manos de resistencia, con apuestas más altas "
                     "permitidas y más fichas de salida.",
        icon="C", color=(120, 200, 120),
        hand_limit=40, starting_chips=1500.0, min_bet=50.0, max_bet=1000.0,
    ),
]

_BY_ID = {t.id: t for t in TOURNAMENTS}


def get_tournament(tournament_id: str) -> Tournament:
    return _BY_ID[tournament_id]
