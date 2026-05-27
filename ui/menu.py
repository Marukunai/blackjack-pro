# ui/menu.py
# Menú principal, pantalla de configuración y selección de preset.
# -------------------------------------------------------------
from __future__ import annotations

import pygame
from typing import Optional, Callable
from config import settings as cfg
from config.rules_presets import PRESETS, get_preset


class MenuItem:
    def __init__(self, text: str, value: str, x: int, y: int, w: int, h: int,
                 font: pygame.font.Font, selected: bool = False) -> None:
        self.text     = text
        self.value    = value
        self.rect     = pygame.Rect(x, y, w, h)
        self.font     = font
        self.selected = selected
        self._hover   = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            self._hover = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True
        return False

    def draw(self, surf: pygame.Surface) -> None:
        if self.selected:
            bg = (212, 175, 55, 40)
            border = cfg.COLOR_GOLD
            text_col = cfg.COLOR_GOLD
        elif self._hover:
            bg = (255, 255, 255, 20)
            border = (200, 200, 200)
            text_col = (255, 255, 255)
        else:
            bg = (0, 0, 0, 0)
            border = (100, 100, 100)
            text_col = (200, 200, 200)

        box = pygame.Surface((self.rect.w, self.rect.h), pygame.SRCALPHA)
        pygame.draw.rect(box, bg, box.get_rect(), border_radius=8)
        pygame.draw.rect(box, border, box.get_rect(), 1, border_radius=8)
        surf.blit(box, (self.rect.x, self.rect.y))

        t = self.font.render(self.text, True, text_col)
        surf.blit(t, (self.rect.centerx - t.get_width()//2,
                      self.rect.centery - t.get_height()//2))


class MainMenu:
    """
    Pantalla de bienvenida: selección de preset, nombre del jugador
    y opciones de configuración. Devuelve (player_name, preset_name)
    cuando el jugador pulsa START.
    """

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.sw, self.sh = screen.get_size()
        self._done   = False
        self._result: Optional[tuple[str, str]] = None

        # Fuentes
        self._font_title  = pygame.font.SysFont(None, 64, bold=True)
        self._font_sub    = pygame.font.SysFont(None, 28, bold=True)
        self._font_body   = pygame.font.SysFont(None, 22)
        self._font_small  = pygame.font.SysFont(None, 18)

        # Estado
        self._name_input  = ""
        self._name_active = False
        self._preset_idx  = 0
        self._preset_names = list(PRESETS.keys())

        # Construir items de preset
        self._preset_items: list[MenuItem] = []
        self._build_preset_items()

        # Botón START
        self._start_rect = pygame.Rect(self.sw//2 - 120, self.sh - 90, 240, 52)
        self._start_hover = False

        # Animación de fondo
        self._anim_offset = 0.0

    # ------------------------------------------------------------------
    def _build_preset_items(self) -> None:
        self._preset_items.clear()
        item_w, item_h, gap = 320, 44, 8
        total_h = len(self._preset_names) * (item_h + gap) - gap
        start_y = self.sh // 2 - total_h // 2 + 30
        x = self.sw // 2 - item_w // 2

        for i, name in enumerate(self._preset_names):
            y = start_y + i * (item_h + gap)
            item = MenuItem(
                text=name, value=name,
                x=x, y=y, w=item_w, h=item_h,
                font=self._font_body,
                selected=(i == self._preset_idx),
            )
            self._preset_items.append(item)

    # ------------------------------------------------------------------
    def run(self) -> tuple[str, str]:
        """Bucle bloqueante. Devuelve (nombre, preset)."""
        clock = pygame.time.Clock()
        while not self._done:
            dt = clock.tick(60)
            self._anim_offset += 0.3

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit
                self._handle_event(event)

            self._draw()
            pygame.display.flip()

        name   = self._name_input.strip() or "Jugador"
        preset = self._preset_names[self._preset_idx]
        return name, preset

    # ------------------------------------------------------------------
    def _handle_event(self, event: pygame.event.Event) -> None:
        # Nombre del jugador
        if event.type == pygame.MOUSEBUTTONDOWN:
            name_rect = pygame.Rect(self.sw//2 - 150, self.sh//2 - 200, 300, 36)
            self._name_active = name_rect.collidepoint(event.pos)
            self._start_hover = self._start_rect.collidepoint(event.pos)
            if self._start_rect.collidepoint(event.pos):
                self._done = True

        if event.type == pygame.MOUSEMOTION:
            self._start_hover = self._start_rect.collidepoint(event.pos)

        if event.type == pygame.KEYDOWN and self._name_active:
            if event.key == pygame.K_BACKSPACE:
                self._name_input = self._name_input[:-1]
            elif event.key == pygame.K_RETURN:
                self._name_active = False
            elif len(self._name_input) < 16 and event.unicode.isprintable():
                self._name_input += event.unicode

        if event.key == pygame.K_RETURN if event.type == pygame.KEYDOWN else False:
            if not self._name_active:
                self._done = True

        # Selección de preset con click o teclado
        for i, item in enumerate(self._preset_items):
            if item.handle_event(event):
                self._preset_idx = i
                for j, it in enumerate(self._preset_items):
                    it.selected = (j == i)

        # Flechas arriba/abajo
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self._preset_idx = max(0, self._preset_idx - 1)
                for j, it in enumerate(self._preset_items):
                    it.selected = (j == self._preset_idx)
            elif event.key == pygame.K_DOWN:
                self._preset_idx = min(len(self._preset_names)-1, self._preset_idx + 1)
                for j, it in enumerate(self._preset_items):
                    it.selected = (j == self._preset_idx)
            elif event.key == pygame.K_RETURN and not self._name_active:
                self._done = True

    # ------------------------------------------------------------------
    def _draw(self) -> None:
        surf = self.screen

        # Fondo degradado oscuro
        surf.fill(cfg.COLOR_BG)
        self._draw_bg_pattern(surf)

        # Título
        title = self._font_title.render("BLACKJACK PRO", True, cfg.COLOR_GOLD)
        shadow = self._font_title.render("BLACKJACK PRO", True, (0, 0, 0))
        tx = self.sw//2 - title.get_width()//2
        surf.blit(shadow, (tx+3, 43))
        surf.blit(title,  (tx,   40))

        sub = self._font_small.render("🃏  Casino Edition  🃏", True, (180, 160, 100))
        surf.blit(sub, (self.sw//2 - sub.get_width()//2, 110))

        # Campo de nombre
        name_rect = pygame.Rect(self.sw//2 - 150, self.sh//2 - 200, 300, 36)
        label = self._font_body.render("Nombre del jugador:", True, cfg.COLOR_TEXT)
        surf.blit(label, (name_rect.x, name_rect.y - 22))

        border_col = cfg.COLOR_GOLD if self._name_active else (120, 120, 120)
        pygame.draw.rect(surf, (20, 20, 20), name_rect, border_radius=6)
        pygame.draw.rect(surf, border_col, name_rect, 1, border_radius=6)

        display_name = self._name_input + ("|" if self._name_active else "")
        name_surf = self._font_body.render(display_name or "Jugador", True,
                                            cfg.COLOR_TEXT if self._name_input else (100, 100, 100))
        surf.blit(name_surf, (name_rect.x + 8, name_rect.y + 8))

        # Separador
        sep_y = self.sh//2 - 148
        pygame.draw.line(surf, (80, 80, 80), (self.sw//2 - 200, sep_y), (self.sw//2 + 200, sep_y), 1)

        # Subtítulo preset
        preset_lbl = self._font_sub.render("Selecciona el casino:", True, cfg.COLOR_TEXT)
        surf.blit(preset_lbl, (self.sw//2 - preset_lbl.get_width()//2, sep_y + 8))

        # Items de preset
        for item in self._preset_items:
            item.draw(surf)

        # Info del preset seleccionado
        preset_name = self._preset_names[self._preset_idx]
        rules = get_preset(preset_name)
        info = self._font_small.render(str(rules), True, (150, 150, 150))
        info_y = self._preset_items[-1].rect.bottom + 10
        surf.blit(info, (self.sw//2 - info.get_width()//2, info_y))

        # Botón START
        start_col = cfg.COLOR_GOLD if self._start_hover else (160, 130, 40)
        pygame.draw.rect(surf, (20, 15, 0), self._start_rect, border_radius=10)
        pygame.draw.rect(surf, start_col, self._start_rect, 2, border_radius=10)
        start_text = self._font_sub.render("▶  JUGAR", True, start_col)
        surf.blit(start_text, (self._start_rect.centerx - start_text.get_width()//2,
                                self._start_rect.centery - start_text.get_height()//2))

        hint = self._font_small.render("↑↓ para seleccionar · Enter para jugar", True, (80, 80, 80))
        surf.blit(hint, (self.sw//2 - hint.get_width()//2, self.sh - 28))

    def _draw_bg_pattern(self, surf: pygame.Surface) -> None:
        """Patrón de rombos animado en el fondo."""
        import math
        col = (35, 100, 55, 18)
        pat = pygame.Surface((self.sw, self.sh), pygame.SRCALPHA)
        step = 60
        offset = int(self._anim_offset % step)
        for x in range(-step + offset, self.sw + step, step):
            for y in range(-step, self.sh + step, step):
                pts = [(x, y-step//2), (x+step//2, y), (x, y+step//2), (x-step//2, y)]
                pygame.draw.polygon(pat, col, pts, 1)
        surf.blit(pat, (0, 0))