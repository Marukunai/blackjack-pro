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

# Versión mostrada en el menú principal y usada por installer.iss (Fase 25:
# hay que mantener ambas en sincronía a mano -- installer.iss no puede leer
# este archivo Python durante la compilación de Inno Setup).
APP_VERSION   = "1.3.0"

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
LANGUAGE = "es"   # "es" | "en" | "fr" | "pt" | "de"

# ------------------------------------------------------------------
# Juego
# ------------------------------------------------------------------
DEFAULT_PRESET    = "Vegas Strip"
ANIMATION_SPEED   = 1.0   # multiplicador (0.5 = lento, 2.0 = rápido)
SHOW_HINTS        = True   # mostrar hints de estrategia básica
SHOW_CARD_COUNTER = False  # mostrar contador Hi-Lo (modo avanzado)
TRAINING_MODE     = False  # Fase 19: corrige cada jugada contra la estrategia básica

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
# Temas visuales (Fase 15): mesa (fieltro) y reverso de carta.
# COLOR_FELT/COLOR_FELT_LIGHT y CARD_BACK_* de más abajo son los valores
# EFECTIVOS que leen ui/table.py y ui/card_generator.py en cada dibujo
# (como atributos de este módulo, no copias importadas) -- por eso
# aplicar un tema en caliente (apply_table_theme / apply_card_back_theme)
# solo necesita reasignar estos nombres; no hay que tocar ui/table.py ni
# ui/card_generator.py cada vez que se añade una paleta nueva.
# ------------------------------------------------------------------
TABLE_THEMES: dict[str, dict] = {
    "classic_green": {"label": "Verde clásico", "felt": (35, 100, 55), "felt_light": (45, 120, 65)},
    "royal_blue":    {"label": "Azul real",      "felt": (20, 45, 95),  "felt_light": (30, 62, 118)},
    "burgundy":      {"label": "Burdeos",        "felt": (85, 24, 34),  "felt_light": (112, 34, 46)},
    "midnight":      {"label": "Negro medianoche", "felt": (28, 28, 32), "felt_light": (44, 44, 50)},
    # Fase 28: 2 fieltros nuevos.
    "emerald_luxe":  {"label": "Esmeralda de lujo", "felt": (8, 72, 48),  "felt_light": (14, 98, 64)},
    "purple_royal":  {"label": "Púrpura real",      "felt": (55, 20, 85), "felt_light": (75, 32, 110)},
}
DEFAULT_TABLE_THEME = "classic_green"

CARD_BACK_THEMES: dict[str, dict] = {
    "green_gold": {"label": "Verde y oro",  "dark": (10, 60, 30),  "light": (20, 100, 50), "pattern": (255, 215, 0, 40)},
    "red_classic": {"label": "Rojo clásico", "dark": (90, 15, 20),  "light": (140, 25, 30), "pattern": (255, 255, 255, 45)},
    "blue_royal": {"label": "Azul real",    "dark": (10, 30, 80),  "light": (20, 50, 120), "pattern": (255, 215, 0, 40)},
    # Fase 28: 2 reversos nuevos.
    "purple_royal": {"label": "Púrpura real", "dark": (45, 10, 70), "light": (75, 20, 110), "pattern": (255, 215, 0, 40)},
    "black_silver": {"label": "Negro y plata", "dark": (15, 15, 18), "light": (38, 38, 44), "pattern": (200, 200, 210, 55)},
}
DEFAULT_CARD_BACK_THEME = "green_gold"

# Reverso de carta -- valores efectivos, leídos por ui/card_generator.py.
CARD_BACK_DARK    = CARD_BACK_THEMES[DEFAULT_CARD_BACK_THEME]["dark"]
CARD_BACK_LIGHT   = CARD_BACK_THEMES[DEFAULT_CARD_BACK_THEME]["light"]
CARD_BACK_PATTERN = CARD_BACK_THEMES[DEFAULT_CARD_BACK_THEME]["pattern"]

CURRENT_TABLE_THEME = DEFAULT_TABLE_THEME
CURRENT_CARD_BACK_THEME = DEFAULT_CARD_BACK_THEME


def apply_table_theme(name: str) -> bool:
    """Cambia el fieltro de la mesa en caliente. Devuelve False si el
    nombre no existe (no cambia nada)."""
    global COLOR_FELT, COLOR_FELT_LIGHT, CURRENT_TABLE_THEME
    theme = TABLE_THEMES.get(name)
    if theme is None:
        return False
    COLOR_FELT = theme["felt"]
    COLOR_FELT_LIGHT = theme["felt_light"]
    CURRENT_TABLE_THEME = name
    return True


def apply_card_back_theme(name: str) -> bool:
    """Cambia el reverso de las cartas en caliente. Devuelve False si el
    nombre no existe (no cambia nada)."""
    global CARD_BACK_DARK, CARD_BACK_LIGHT, CARD_BACK_PATTERN, CURRENT_CARD_BACK_THEME
    theme = CARD_BACK_THEMES.get(name)
    if theme is None:
        return False
    CARD_BACK_DARK = theme["dark"]
    CARD_BACK_LIGHT = theme["light"]
    CARD_BACK_PATTERN = theme["pattern"]
    CURRENT_CARD_BACK_THEME = name
    return True

# ------------------------------------------------------------------
# Tamaños de cartas en pantalla
# ------------------------------------------------------------------
CARD_WIDTH  = 80
CARD_HEIGHT = 112
CARD_RADIUS = 8    # radio de esquinas redondeadas