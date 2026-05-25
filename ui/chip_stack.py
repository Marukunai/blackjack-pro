# ui/chip_stack.py
# Fichas de casino clicables para apostar.
# -------------------------------------------------------------
from __future__ import annotations

import pygame
from typing import Callable, Optional
from config import settings as cfg

# Denominaciones y colores (estándar de casino)
CHIP_DEFS = [
    (5,    (230, 230, 230), (80,  80,  80)),   # blanco/gris   $5
    (10,   (220, 60,  60),  (255, 255, 255)),  # rojo          $10
    (25,   (50,  160, 80),  (255, 255, 255)),  # verde         $25
    (50,   (60,  60,  200), (255, 255, 255)),  # azul          $50
    (100,  (60,  20,  20),  (255, 215, 0)),    # negro/dorado  $100
    (500,  (80,  20,  120), (255, 215, 0)),    # morado        $500
]

CHIP_R   = 26   # radio
CHIP_GAP = 10   # espacio entre fichas


class Chip:
    def __init__(self, value: int, bg: tuple, text_col: tuple,
                 x: int, y: int, callback: Callable) -> None:
        self.value    = value
        self.bg       = bg
        self.text_col = text_col
        self.center   = (x, y)
        self.callback = callback
        self._hover   = False
        self._font: Optional[pygame.font.Font] = None

    def _ensure_font(self) -> None:
        if self._font is None:
            self._font = pygame.font.SysFont(None, 17, bold=True)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            dx = event.pos[0] - self.center[0]
            dy = event.pos[1] - self.center[1]
            self._hover = (dx*dx + dy*dy) <= CHIP_R * CHIP_R
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            dx = event.pos[0] - self.center[0]
            dy = event.pos[1] - self.center[1]
            if (dx*dx + dy*dy) <= CHIP_R * CHIP_R:
                self.callback(self.value)
                return True
        return False

    def draw(self, surf: pygame.Surface, enabled: bool = True) -> None:
        self._ensure_font()
        r = CHIP_R
        cx, cy = self.center

        alpha = 255 if enabled else 100
        col = self.bg if enabled else (80, 80, 80)

        # Sombra
        pygame.draw.circle(surf, (0, 0, 0, 60), (cx+2, cy+2), r)

        # Fondo principal
        pygame.draw.circle(surf, col, (cx, cy), r)

        # Anillo exterior
        ring_col = tuple(min(255, c + 50) for c in col) if enabled else (100, 100, 100)
        pygame.draw.circle(surf, ring_col, (cx, cy), r, 3)

        # Líneas decorativas interiores (estilo ficha de casino)
        inner_r = int(r * 0.72)
        pygame.draw.circle(surf, ring_col, (cx, cy), inner_r, 1)

        # Muescas en la ficha (4 puntos)
        import math
        notch_col = ring_col
        for angle in range(0, 360, 90):
            rad = math.radians(angle)
            nx = int(cx + (r - 4) * math.cos(rad))
            ny = int(cy + (r - 4) * math.sin(rad))
            pygame.draw.circle(surf, notch_col, (nx, ny), 3)

        # Texto del valor
        label = f"${self.value}" if self.value < 1000 else f"${self.value//1000}K"
        text_col = self.text_col if enabled else (150, 150, 150)
        t = self._font.render(label, True, text_col)
        surf.blit(t, (cx - t.get_width()//2, cy - t.get_height()//2))

        # Brillo hover
        if self._hover and enabled:
            glow = pygame.Surface((r*2+8, r*2+8), pygame.SRCALPHA)
            pygame.draw.circle(glow, (255, 255, 255, 40), (r+4, r+4), r+4)
            surf.blit(glow, (cx - r - 4, cy - r - 4))


class ChipTray:
    """
    Bandeja de fichas en la parte inferior de la pantalla.
    Click en una ficha → añade esa cantidad a la apuesta actual.
    """

    def __init__(self, screen_w: int, screen_h: int, callback: Callable) -> None:
        """callback(amount: int) se llama al pulsar una ficha."""
        self._callback = callback
        self._chips: list[Chip] = []
        self._enabled = True
        self._build(screen_w, screen_h)
        self._font: Optional[pygame.font.Font] = None

    def _build(self, sw: int, sh: int) -> None:
        n = len(CHIP_DEFS)
        total_w = n * (CHIP_R*2) + (n-1) * CHIP_GAP
        start_x = sw // 2 - total_w // 2 + CHIP_R
        y = sh - CHIP_R - 80   # encima de los botones

        for i, (value, bg, text_col) in enumerate(CHIP_DEFS):
            x = start_x + i * (CHIP_R*2 + CHIP_GAP)
            chip = Chip(value, bg, text_col, x, y, self._callback)
            self._chips.append(chip)

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self._enabled:
            return False
        for chip in self._chips:
            if chip.handle_event(event):
                return True
        return False

    def draw(self, surf: pygame.Surface, current_bet: int = 0,
             min_bet: int = 5, max_bet: int = 1000, chips: int = 1000) -> None:
        if self._font is None:
            self._font = pygame.font.SysFont(None, 20, bold=True)

        for chip in self._chips:
            can_add = (self._enabled and
                       current_bet + chip.value <= max_bet and
                       chip.value <= chips)
            chip.draw(surf, enabled=can_add)

        # Apuesta actual
        if current_bet > 0:
            bet_text = self._font.render(f"Apuesta: ${current_bet}", True, cfg.COLOR_GOLD)
            # Centrar sobre las fichas
            y = self._chips[0].center[1] - CHIP_R - bet_text.get_height() - 4
            surf.blit(bet_text, (surf.get_width()//2 - bet_text.get_width()//2, y))