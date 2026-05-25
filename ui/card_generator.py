# ui/card_generator.py
# Generación procedural de cartas de casino con Pygame.
# Produce superficies listas para usar; si existe un PNG en assets/cards/
# lo carga en su lugar, permitiendo sustituir los assets fácilmente.
# -------------------------------------------------------------
from __future__ import annotations

import math
from pathlib import Path
from typing import Optional

import pygame

from config import settings as cfg


# ── Paleta de la carta ────────────────────────────────────────────────
CARD_BG         = (252, 248, 240)   # marfil cálido
CARD_BORDER     = (180, 160, 120)   # dorado apagado
CARD_SHADOW     = (30,  30,  30,  80)
RED_SUIT        = (196, 30,  30)
BLACK_SUIT      = (15,  15,  15)
BACK_DARK       = (10,  60,  30)    # verde oscuro casino
BACK_LIGHT      = (20,  100, 50)
BACK_PATTERN    = (255, 215, 0,  40)  # dorado semitransparente

# ── Símbolos unicode de palos ─────────────────────────────────────────
SUIT_SYMBOL = {"♠": "♠", "♥": "♥", "♦": "♦", "♣": "♣"}
SUIT_COLOR  = {
    "♠": BLACK_SUIT, "♣": BLACK_SUIT,
    "♥": RED_SUIT,   "♦": RED_SUIT,
}

# ── Posiciones de los símbolos en el interior (grid 3×7) ─────────────
# Cada tupla es (x_frac, y_frac) del área interior de la carta
PIP_LAYOUT: dict[int, list[tuple[float, float]]] = {
    1:  [(0.50, 0.50)],
    2:  [(0.50, 0.25), (0.50, 0.75)],
    3:  [(0.50, 0.20), (0.50, 0.50), (0.50, 0.80)],
    4:  [(0.30, 0.25), (0.70, 0.25), (0.30, 0.75), (0.70, 0.75)],
    5:  [(0.30, 0.25), (0.70, 0.25), (0.50, 0.50), (0.30, 0.75), (0.70, 0.75)],
    6:  [(0.30, 0.22), (0.70, 0.22), (0.30, 0.50), (0.70, 0.50), (0.30, 0.78), (0.70, 0.78)],
    7:  [(0.30, 0.22), (0.70, 0.22), (0.50, 0.36), (0.30, 0.50), (0.70, 0.50), (0.30, 0.78), (0.70, 0.78)],
    8:  [(0.30, 0.20), (0.70, 0.20), (0.30, 0.40), (0.70, 0.40), (0.30, 0.60), (0.70, 0.60), (0.30, 0.80), (0.70, 0.80)],
    9:  [(0.30, 0.18), (0.70, 0.18), (0.30, 0.36), (0.70, 0.36), (0.50, 0.50),
         (0.30, 0.64), (0.70, 0.64), (0.30, 0.82), (0.70, 0.82)],
    10: [(0.30, 0.16), (0.70, 0.16), (0.50, 0.28), (0.30, 0.40), (0.70, 0.40),
         (0.30, 0.60), (0.70, 0.60), (0.50, 0.72), (0.30, 0.84), (0.70, 0.84)],
}


class CardGenerator:
    """
    Genera y cachea superficies Pygame para todas las cartas y el reverso.

    Uso:
        gen = CardGenerator()
        surf = gen.get("AH")    # As de corazones
        surf = gen.get_back()   # reverso
    """

    def __init__(self, width: int = cfg.CARD_WIDTH, height: int = cfg.CARD_HEIGHT) -> None:
        self.w = width
        self.h = height
        self._cache: dict[str, pygame.Surface] = {}
        self._back: Optional[pygame.Surface] = None
        self._font_rank_large: Optional[pygame.font.Font] = None
        self._font_rank_small: Optional[pygame.font.Font] = None
        self._font_suit_large: Optional[pygame.font.Font] = None
        self._font_suit_small: Optional[pygame.font.Font] = None
        self._font_face:       Optional[pygame.font.Font] = None

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def get(self, asset_name: str) -> pygame.Surface:
        """Devuelve la superficie de una carta por su asset_name (p.ej. 'AH.png')."""
        key = asset_name.replace(".png", "")
        if key not in self._cache:
            self._cache[key] = self._load_or_generate(asset_name)
        return self._cache[key]

    def get_back(self) -> pygame.Surface:
        if self._back is None:
            self._back = self._draw_back()
        return self._back

    def get_hidden(self) -> pygame.Surface:
        return self.get_back()

    # ------------------------------------------------------------------
    # Carga o generación
    # ------------------------------------------------------------------
    def _load_or_generate(self, asset_name: str) -> pygame.Surface:
        path = cfg.CARDS_DIR / asset_name
        if path.exists():
            try:
                img = pygame.image.load(str(path)).convert_alpha()
                return pygame.transform.smoothscale(img, (self.w, self.h))
            except Exception:
                pass
        # Generar proceduralmente
        return self._draw_card(asset_name.replace(".png", ""))

    def _init_fonts(self) -> None:
        if self._font_rank_large:
            return
        # Intentar fuente del sistema con soporte unicode
        candidates = ["segoeuisymbol", "dejavusans", "freesans", "arial", None]
        font_path = None
        for name in candidates:
            try:
                f = pygame.font.SysFont(name, 10)
                font_path = name
                break
            except Exception:
                continue

        sz_large = max(10, int(self.h * 0.18))
        sz_small = max(8,  int(self.h * 0.12))
        sz_suit  = max(12, int(self.h * 0.22))
        sz_face  = max(16, int(self.h * 0.38))
        sz_pip   = max(10, int(self.h * 0.13))

        self._font_rank_large = pygame.font.SysFont(font_path, sz_large, bold=True)
        self._font_rank_small = pygame.font.SysFont(font_path, sz_small, bold=True)
        self._font_suit_large = pygame.font.SysFont(font_path, sz_suit)
        self._font_suit_small = pygame.font.SysFont(font_path, sz_pip)
        self._font_face       = pygame.font.SysFont(font_path, sz_face, bold=True)

    # ------------------------------------------------------------------
    # Dibujo de carta
    # ------------------------------------------------------------------
    def _draw_card(self, key: str) -> pygame.Surface:
        """key p.ej. 'AH', '10S', 'KD'"""
        self._init_fonts()
        surf = pygame.Surface((self.w, self.h), pygame.SRCALPHA)

        # Determinar rango y palo
        if key[:-1] in ("10",):
            rank, suit_letter = "10", key[-1]
        else:
            rank, suit_letter = key[0], key[1:]

        suit_map = {"S": "♠", "H": "♥", "D": "♦", "C": "♣"}
        suit = suit_map.get(suit_letter, "♠")
        color = SUIT_COLOR.get(suit, BLACK_SUIT)

        r = cfg.CARD_RADIUS
        w, h = self.w, self.h

        # Sombra
        shadow = pygame.Surface((w, h), pygame.SRCALPHA)
        self._rounded_rect(shadow, (0, 0, 0, 60), pygame.Rect(2, 3, w-2, h-2), r)
        surf.blit(shadow, (0, 0))

        # Fondo blanco-marfil
        self._rounded_rect(surf, CARD_BG, pygame.Rect(0, 0, w, h), r)

        # Borde dorado
        self._rounded_rect_border(surf, CARD_BORDER, pygame.Rect(0, 0, w, h), r, 1)

        # Rango esquina superior-izquierda
        pad = max(3, int(w * 0.07))
        rank_surf = self._font_rank_large.render(rank, True, color)
        surf.blit(rank_surf, (pad, pad))

        # Palo bajo el rango
        suit_surf = self._font_suit_small.render(suit, True, color)
        surf.blit(suit_surf, (pad, pad + rank_surf.get_height()))

        # Esquina inferior-derecha (girado 180°)
        rank_r = pygame.transform.rotate(rank_surf, 180)
        suit_r = pygame.transform.rotate(suit_surf, 180)
        surf.blit(rank_r, (w - rank_r.get_width() - pad, h - rank_r.get_height() - suit_r.get_height() - pad))
        surf.blit(suit_r, (w - suit_r.get_width() - pad, h - suit_r.get_height() - pad))

        # Contenido central
        if rank in ("J", "Q", "K", "A"):
            self._draw_face_center(surf, rank, suit, color)
        else:
            self._draw_pips(surf, int(rank), suit, color)

        return surf

    def _draw_pips(self, surf: pygame.Surface, count: int, suit: str, color: tuple) -> None:
        """Dibuja los símbolos numéricos en su posición de cuadrícula."""
        positions = PIP_LAYOUT.get(count, [])
        pad_x = int(self.w * 0.15)
        pad_y = int(self.h * 0.18)
        area_w = self.w - 2 * pad_x
        area_h = self.h - 2 * pad_y

        for (fx, fy) in positions:
            x = int(pad_x + fx * area_w)
            y = int(pad_y + fy * area_h)
            sym = self._font_suit_small.render(suit, True, color)
            # Los pips de la mitad inferior se invierten
            if fy > 0.5:
                sym = pygame.transform.rotate(sym, 180)
            sx = x - sym.get_width() // 2
            sy = y - sym.get_height() // 2
            surf.blit(sym, (sx, sy))

    def _draw_face_center(self, surf: pygame.Surface, rank: str, suit: str, color: tuple) -> None:
        """Dibuja la letra central grande para J/Q/K/A."""
        # Marco decorativo interior
        inner = pygame.Rect(
            int(self.w * 0.15), int(self.h * 0.20),
            int(self.w * 0.70), int(self.h * 0.60)
        )
        self._rounded_rect_border(surf, (*color, 40), inner, 4, 1)

        # Letra grande
        letter = self._font_face.render(rank, True, color)
        cx = (self.w - letter.get_width()) // 2
        cy = (self.h - letter.get_height()) // 2
        surf.blit(letter, (cx, cy))

        # Palo grande centrado bajo la letra
        big_suit = self._font_suit_large.render(suit, True, (*color, 160))
        sx = (self.w - big_suit.get_width()) // 2
        sy = cy + letter.get_height() - int(self.h * 0.04)
        surf.blit(big_suit, (sx, sy))

    # ------------------------------------------------------------------
    # Reverso de la carta
    # ------------------------------------------------------------------
    def _draw_back(self) -> pygame.Surface:
        self._init_fonts()
        surf = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        r = cfg.CARD_RADIUS
        w, h = self.w, self.h

        # Sombra
        shadow = pygame.Surface((w, h), pygame.SRCALPHA)
        self._rounded_rect(shadow, (0, 0, 0, 60), pygame.Rect(2, 3, w-2, h-2), r)
        surf.blit(shadow, (0, 0))

        # Fondo verde oscuro
        self._rounded_rect(surf, BACK_DARK, pygame.Rect(0, 0, w, h), r)

        # Patrón de rombos
        self._draw_back_pattern(surf)

        # Marco interior dorado
        inner = pygame.Rect(int(w*0.08), int(h*0.05), int(w*0.84), int(h*0.90))
        self._rounded_rect_border(surf, cfg.COLOR_GOLD, inner, max(2, r-2), 1)

        # Borde exterior
        self._rounded_rect_border(surf, cfg.COLOR_GOLD, pygame.Rect(0, 0, w, h), r, 1)

        return surf

    def _draw_back_pattern(self, surf: pygame.Surface) -> None:
        """Patrón de rombos diagonales estilo casino."""
        w, h = self.w, self.h
        step = max(6, int(w * 0.18))
        col = (255, 215, 0, 35)
        pat = pygame.Surface((w, h), pygame.SRCALPHA)
        for x in range(-h, w + h, step):
            pts = [(x, 0), (x + step//2, h//2), (x, h), (x - step//2, h//2)]
            if len(pts) >= 3:
                pygame.draw.polygon(pat, col, pts, 1)
        surf.blit(pat, (0, 0))

    # ------------------------------------------------------------------
    # Helpers de dibujo
    # ------------------------------------------------------------------
    @staticmethod
    def _rounded_rect(surf: pygame.Surface, color: tuple, rect: pygame.Rect, radius: int) -> None:
        pygame.draw.rect(surf, color, rect, border_radius=radius)

    @staticmethod
    def _rounded_rect_border(surf: pygame.Surface, color: tuple, rect: pygame.Rect, radius: int, width: int) -> None:
        pygame.draw.rect(surf, color, rect, width=width, border_radius=radius)