# ui/side_bets_ui.py
# Selector de apuestas laterales (Parejas Perfectas / 21+3) en la fase de
# apuesta: dos "steppers" independientes (flechas ◄ ►, mismo estilo visual
# que _RuleRow en ui/menu.py) que recorren una lista fija de importes, para
# no poder escribir un valor inválido. Solo se muestran si la regla
# correspondiente está activa en la partida actual.
# -------------------------------------------------------------
from __future__ import annotations

import pygame
from typing import Optional

from config import settings as cfg
from config import i18n
from ui import icons

# Importes disponibles para cada apuesta lateral; 0 = sin apostar.
STEP_VALUES = (0, 5, 10, 25, 50, 100)

BOX_W, BOX_H = 240, 46
GAP = 20


class _SideBetStepper:
    def __init__(self, kind: str, label: str, x: int, y: int,
                 font: pygame.font.Font, font_small: pygame.font.Font) -> None:
        self.kind = kind
        self.label = label
        self.rect = pygame.Rect(x, y, BOX_W, BOX_H)
        self.font = font
        self.font_small = font_small
        self.index = 0
        self.enabled = True

    @property
    def value(self) -> int:
        return STEP_VALUES[self.index]

    def reset(self) -> None:
        self.index = 0

    def _max_index_for(self, side_bet_max: float, chips: float) -> int:
        idx = len(STEP_VALUES) - 1
        while idx > 0 and (STEP_VALUES[idx] > side_bet_max or STEP_VALUES[idx] > chips):
            idx -= 1
        return idx

    def clamp(self, side_bet_max: float, chips: float) -> None:
        max_idx = self._max_index_for(side_bet_max, chips)
        if self.index > max_idx:
            self.index = max_idx

    def arrow_rects(self) -> tuple[pygame.Rect, pygame.Rect]:
        size = self.rect.h - 16
        cy = self.rect.y + (self.rect.h - size) // 2
        left = pygame.Rect(self.rect.x + 8, cy, size, size)
        right = pygame.Rect(self.rect.right - 8 - size, cy, size, size)
        return left, right

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            left_rect, right_rect = self.arrow_rects()
            if left_rect.collidepoint(event.pos):
                self.index = max(0, self.index - 1)
                return True
            if right_rect.collidepoint(event.pos):
                self.index = min(len(STEP_VALUES) - 1, self.index + 1)
                return True
        return False

    def draw(self, surf: pygame.Surface) -> None:
        active = self.value > 0
        bg = (212, 175, 55, 28) if active else (255, 255, 255, 8)
        border = cfg.COLOR_GOLD if active else (100, 100, 100)
        box = pygame.Surface((self.rect.w, self.rect.h), pygame.SRCALPHA)
        pygame.draw.rect(box, bg, box.get_rect(), border_radius=8)
        pygame.draw.rect(box, border, box.get_rect(), 1, border_radius=8)
        surf.blit(box, (self.rect.x, self.rect.y))

        label_col = cfg.COLOR_TEXT if active else (160, 160, 160)
        lbl = self.font_small.render(self.label, True, label_col)
        surf.blit(lbl, (self.rect.centerx - lbl.get_width() // 2, self.rect.y + 4))

        left_rect, right_rect = self.arrow_rects()
        arrow_col = cfg.COLOR_GOLD if self.enabled else (90, 90, 90)
        icons.triangle_left(surf, left_rect.right - 4, left_rect.centery + 6, left_rect.h * 0.5, arrow_col)
        icons.triangle_right(surf, right_rect.x + 4, right_rect.centery + 6, right_rect.h * 0.5, arrow_col)

        val_text = f"${self.value}" if self.value > 0 else "—"
        val_col = cfg.COLOR_GOLD if active else (170, 170, 170)
        val = self.font.render(val_text, True, val_col)
        surf.blit(val, (self.rect.centerx - val.get_width() // 2, self.rect.centery + 4))


class SideBetPanel:
    """Agrupa los steppers de apuestas laterales activos para esta partida
    (según Rules) y los coloca centrados en una fila, en la zona libre de
    fieltro justo encima de la bandeja de fichas principal."""

    def __init__(self, sw: int, sh: int, perfect_pairs_allowed: bool,
                 twentyone_plus_three_allowed: bool) -> None:
        self.sw, self.sh = sw, sh
        self._font = pygame.font.SysFont(None, 20, bold=True)
        self._font_small = pygame.font.SysFont(None, 16)

        self.steppers: list[_SideBetStepper] = []
        kinds = []
        if perfect_pairs_allowed:
            kinds.append(("perfect_pairs", i18n.t("sidebets.perfect_pairs_label")))
        if twentyone_plus_three_allowed:
            kinds.append(("21+3", "21+3"))

        n = len(kinds)
        total_w = n * BOX_W + max(0, n - 1) * GAP
        start_x = sw // 2 - total_w // 2
        y = sh - 218
        for i, (kind, label) in enumerate(kinds):
            x = start_x + i * (BOX_W + GAP)
            self.steppers.append(_SideBetStepper(kind, label, x, y, self._font, self._font_small))

    @property
    def has_bets(self) -> bool:
        return any(s.value > 0 for s in self.steppers)

    def value_for(self, kind: str) -> float:
        for s in self.steppers:
            if s.kind == kind:
                return float(s.value)
        return 0.0

    def reset(self) -> None:
        for s in self.steppers:
            s.reset()

    def set_enabled(self, enabled: bool) -> None:
        for s in self.steppers:
            s.enabled = enabled

    def clamp_to(self, side_bet_max: float, chips: float) -> None:
        for s in self.steppers:
            s.clamp(side_bet_max, chips)

    def handle_event(self, event: pygame.event.Event) -> bool:
        handled = False
        for s in self.steppers:
            if s.handle_event(event):
                handled = True
        return handled

    def draw(self, surf: pygame.Surface) -> None:
        if not self.steppers:
            return
        title = self._font_small.render(i18n.t("sidebets.title"), True, (150, 150, 150))
        top_y = self.steppers[0].rect.y - 20
        surf.blit(title, (self.sw // 2 - title.get_width() // 2, top_y))
        for s in self.steppers:
            s.draw(surf)
