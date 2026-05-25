# ui/buttons.py
# Botones de acción contextuales con hover, disabled y tecla de atajo.
# -------------------------------------------------------------
from __future__ import annotations

import pygame
from typing import Optional, Callable
from config import settings as cfg


# ── Paleta de botones ────────────────────────────────────────────────
BTN_COLORS = {
    "hit":        ((50,  160, 70),  (70,  200, 90)),   # verde
    "stand":      ((180, 50,  50),  (220, 70,  70)),   # rojo
    "double":     ((200, 140, 0),   (240, 170, 0)),    # naranja
    "split":      ((50,  100, 200), (70,  130, 240)),  # azul
    "surrender":  ((130, 50,  160), (160, 70,  200)),  # morado
    "insurance":  ((30,  130, 160), (50,  160, 200)),  # cian
    "deal":       ((50,  160, 70),  (70,  200, 90)),   # verde
    "rebet":      ((100, 80,  160), (130, 100, 200)),  # violeta
    "yes":        ((50,  160, 70),  (70,  200, 90)),
    "no":         ((180, 50,  50),  (220, 70,  70)),
    "default":    ((80,  80,  80),  (110, 110, 110)),
}

BTN_TEXT_COLOR  = (255, 255, 255)
BTN_DIS_BG      = (60,  60,  60)
BTN_DIS_TEXT    = (120, 120, 120)
BTN_BORDER      = (255, 255, 255, 40)
BTN_RADIUS      = 8
BTN_H           = 44
BTN_W           = 110


class Button:
    def __init__(
        self,
        action: str,
        label: str,
        shortcut: str,
        x: int, y: int,
        w: int = BTN_W,
        h: int = BTN_H,
        callback: Optional[Callable] = None,
    ) -> None:
        self.action   = action
        self.label    = label
        self.shortcut = shortcut.upper()
        self.rect     = pygame.Rect(x, y, w, h)
        self.callback = callback
        self.enabled  = True
        self._hover   = False
        self._pressed = False
        self._font: Optional[pygame.font.Font] = None
        self._font_key: Optional[pygame.font.Font] = None

    def _ensure_fonts(self) -> None:
        if self._font is None:
            self._font     = pygame.font.SysFont(None, 20, bold=True)
            self._font_key = pygame.font.SysFont(None, 15)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Devuelve True si el botón fue activado."""
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEMOTION:
            self._hover = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self._pressed = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._pressed and self.rect.collidepoint(event.pos):
                self._pressed = False
                if self.callback:
                    self.callback(self.action)
                return True
            self._pressed = False
        elif event.type == pygame.KEYDOWN:
            if event.unicode.upper() == self.shortcut:
                if self.callback:
                    self.callback(self.action)
                return True
        return False

    def draw(self, surf: pygame.Surface) -> None:
        self._ensure_fonts()
        colors = BTN_COLORS.get(self.action, BTN_COLORS["default"])

        if not self.enabled:
            bg = BTN_DIS_BG
            text_col = BTN_DIS_TEXT
        elif self._pressed:
            bg = colors[0]
            text_col = BTN_TEXT_COLOR
        elif self._hover:
            bg = colors[1]
            text_col = BTN_TEXT_COLOR
        else:
            # Degradado simple: mezcla de los dos colores
            bg = tuple(int((a + b) / 2) for a, b in zip(colors[0], colors[1]))
            text_col = BTN_TEXT_COLOR

        # Fondo
        pygame.draw.rect(surf, bg, self.rect, border_radius=BTN_RADIUS)

        # Borde superior claro (efecto 3D)
        if self.enabled and not self._pressed:
            highlight = pygame.Rect(self.rect.x, self.rect.y, self.rect.w, 2)
            light = tuple(min(255, c + 60) for c in bg)
            pygame.draw.rect(surf, light, highlight, border_radius=BTN_RADIUS)

        # Borde exterior
        pygame.draw.rect(surf, (255, 255, 255, 30), self.rect, 1, border_radius=BTN_RADIUS)

        # Texto principal
        text_surf = self._font.render(self.label, True, text_col)
        tx = self.rect.centerx - text_surf.get_width() // 2
        ty = self.rect.centery - text_surf.get_height() // 2 - 3
        surf.blit(text_surf, (tx, ty))

        # Tecla de atajo
        key_surf = self._font_key.render(f"[{self.shortcut}]", True,
                                          (*text_col[:3], 160) if self.enabled else BTN_DIS_TEXT)
        kx = self.rect.centerx - key_surf.get_width() // 2
        ky = ty + text_surf.get_height() + 1
        surf.blit(key_surf, (kx, ky))


class ButtonBar:
    """Barra horizontal de botones de acción."""

    ACTION_DEFS = [
        ("hit",       "Hit",       "H"),
        ("stand",     "Stand",     "S"),
        ("double",    "Double",    "D"),
        ("split",     "Split",     "P"),
        ("surrender", "Surrender", "R"),
    ]

    def __init__(self, screen_w: int, screen_h: int, callback: Callable) -> None:
        self.buttons: list[Button] = []
        self._callback = callback
        self._build(screen_w, screen_h)

    def _build(self, sw: int, sh: int) -> None:
        n = len(self.ACTION_DEFS)
        gap = 10
        total_w = n * BTN_W + (n - 1) * gap
        start_x = (sw - total_w) // 2
        y = sh - BTN_H - 18

        for i, (action, label, key) in enumerate(self.ACTION_DEFS):
            x = start_x + i * (BTN_W + gap)
            btn = Button(action, label, key, x, y, callback=self._callback)
            self.buttons.append(btn)

    def set_available(self, actions: list[str]) -> None:
        for btn in self.buttons:
            btn.enabled = btn.action in actions

    def handle_event(self, event: pygame.event.Event) -> bool:
        for btn in self.buttons:
            if btn.handle_event(event):
                return True
        return False

    def draw(self, surf: pygame.Surface) -> None:
        for btn in self.buttons:
            btn.draw(surf)


class InsuranceBar:
    """Barra especial para decisión de seguro / even money."""

    def __init__(self, screen_w: int, screen_h: int,
                 callback: Callable, is_even_money: bool = False) -> None:
        label_yes = "Even Money" if is_even_money else "Seguro (Sí)"
        label_no  = "No"
        gap = 20
        y = screen_h - BTN_H - 18
        cx = screen_w // 2
        self.btn_yes = Button("yes", label_yes, "Y", cx - BTN_W - gap//2, y, callback=callback)
        self.btn_no  = Button("no",  label_no,  "N", cx + gap//2,          y, callback=callback)
        self._font: Optional[pygame.font.Font] = None

    def _ensure_font(self) -> None:
        if self._font is None:
            self._font = pygame.font.SysFont(None, 22, bold=True)

    def handle_event(self, event: pygame.event.Event) -> bool:
        return self.btn_yes.handle_event(event) or self.btn_no.handle_event(event)

    def draw(self, surf: pygame.Surface, message: str = "") -> None:
        self._ensure_font()
        if message:
            text = self._font.render(message, True, cfg.COLOR_GOLD)
            x = surf.get_width() // 2 - text.get_width() // 2
            y = self.btn_yes.rect.y - text.get_height() - 8
            surf.blit(text, (x, y))
        self.btn_yes.draw(surf)
        self.btn_no.draw(surf)