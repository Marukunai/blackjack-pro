# config/settings.py
# Configuración global de la aplicación (resolución, audio, rutas…).
# -------------------------------------------------------------
from __future__ import annotations
from pathlib import Path


# ------------------------------------------------------------------
# Rutas base
# ------------------------------------------------------------------
ROOT_DIR    = Path(__file__).resolve().parent.parent
ASSETS_DIR  = ROOT_DIR / "assets"
SAVES_DIR   = ROOT_DIR / "saves"

CARDS_DIR   = ASSETS_DIR / "cards"
CHIPS_DIR   = ASSETS_DIR / "chips"
FONTS_DIR   = ASSETS_DIR / "fonts"
SOUNDS_DIR  = ASSETS_DIR / "sounds"
BG_DIR      = ASSETS_DIR / "bg"

# ------------------------------------------------------------------
# Pantalla
# ------------------------------------------------------------------
SCREEN_WIDTH  = 1280
SCREEN_HEIGHT = 800
FPS           = 60
WINDOW_TITLE  = "Blackjack Pro"
FULLSCREEN    = False

# ------------------------------------------------------------------
# Audio
# ------------------------------------------------------------------
MUSIC_VOLUME  = 0.4   # 0.0 – 1.0
SFX_VOLUME    = 0.8
MUSIC_ENABLED = True
SFX_ENABLED   = True

# ------------------------------------------------------------------
# Idioma
# ------------------------------------------------------------------
LANGUAGE = "es"   # "es" | "en"

# ------------------------------------------------------------------
# Juego
# ------------------------------------------------------------------
DEFAULT_PRESET    = "Vegas Strip"
ANIMATION_SPEED   = 1.0   # multiplicador (0.5 = lento, 2.0 = rápido)
SHOW_HINTS        = True   # mostrar hints de estrategia básica
SHOW_CARD_COUNTER = False  # mostrar contador Hi-Lo (modo avanzado)
CARD_BACK_STYLE   = "red"  # "red" | "blue" | "pattern"

# ------------------------------------------------------------------
# Colores de la UI (respaldo si no se cargan texturas)
# ------------------------------------------------------------------
COLOR_FELT        = (35, 100, 55)    # verde fieltro
COLOR_FELT_LIGHT  = (45, 120, 65)
COLOR_GOLD        = (212, 175, 55)
COLOR_CHIP_TEXT   = (255, 255, 255)
COLOR_BG          = (20, 20, 20)
COLOR_TEXT        = (230, 230, 230)
COLOR_WIN         = (80, 220, 80)
COLOR_LOSE        = (220, 60, 60)
COLOR_PUSH        = (200, 200, 60)
COLOR_BJ          = (255, 215, 0)    # dorado para Blackjack

# ------------------------------------------------------------------
# Tamaños de cartas en pantalla
# ------------------------------------------------------------------
CARD_WIDTH  = 80
CARD_HEIGHT = 112
CARD_RADIUS = 8    # radio de esquinas redondeadas