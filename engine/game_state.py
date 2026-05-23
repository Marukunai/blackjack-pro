# engine/game_state.py
# Máquina de estados del juego.
# -------------------------------------------------------------
from __future__ import annotations
from enum import Enum, auto


class GameState(Enum):
    """
    Estados del ciclo de vida de una partida.

    Flujo normal:
        MENU → BETTING → DEALING → PLAYER_TURN → DEALER_TURN → PAYOUT → BETTING
                                                                       ↘ GAME_OVER (sin fichas)
    """

    MENU        = auto()   # pantalla de inicio / configuración
    BETTING     = auto()   # el jugador coloca su apuesta
    DEALING     = auto()   # reparto inicial (2 cartas jugador + 2 crupier)
    INSURANCE   = auto()   # oferta de seguro (solo si el crupier muestra As)
    PLAYER_TURN = auto()   # turno del jugador (hit/stand/double/split/surrender)
    DEALER_TURN = auto()   # turno automático del crupier
    PAYOUT      = auto()   # resolución y distribución de fichas
    GAME_OVER   = auto()   # el jugador se queda sin fichas


class ActionResult(Enum):
    """Resultado de ejecutar una acción del jugador."""
    OK            = auto()   # acción aceptada y ejecutada
    BUST          = auto()   # el jugador se ha pasado
    BLACKJACK     = auto()   # blackjack natural
    TWENTY_ONE    = auto()   # 21 sin ser blackjack
    STAND         = auto()   # jugador ha plantado
    SURRENDER     = auto()   # jugador se ha rendido
    SPLIT_DONE    = auto()   # split ejecutado, se avanza a nueva mano
    INVALID       = auto()   # la acción no está permitida en este momento


class RoundResult(Enum):
    """Resultado final de una mano al comparar con el crupier."""
    WIN           = auto()   # jugador gana
    BLACKJACK_WIN = auto()   # blackjack natural (pago especial)
    LOSS          = auto()   # jugador pierde
    PUSH          = auto()   # empate
    SURRENDER     = auto()   # rendición (devuelve mitad)
    DEALER_BUST   = auto()   # el crupier se pasó (jugador gana)