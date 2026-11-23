# ui/tutorial_screen.py
# Fase 36: pantalla de tutorial / "cómo jugar" -- explica las reglas
# básicas, el flujo de una ronda, las acciones disponibles y las
# apuestas laterales, en varias páginas navegables. Se abre desde un
# botón nuevo en MainMenu (ver ui/menu.py); no afecta a ninguna
# partida en curso ni requiere perfil/engine, así que puede mostrarse
# en cualquier momento desde el menú. Mismo patrón de bucle bloqueante
# que el resto de pantallas de apoyo (ChallengeSelect, SettingsScreen,
# BackupBrowseScreen...).
# -------------------------------------------------------------
from __future__ import annotations

import pygame

from config import settings as cfg
from config import i18n
from ui import icons


def _wrap_text(font: pygame.font.Font, text: str, max_w: int) -> list[str]:
    words = text.split(" ")
    lines: list[str] = []
    cur = ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if font.size(trial)[0] <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


class TutorialScreen:
    """Bucle bloqueante. No devuelve nada (Optional[None]): es puramente
    informativa, se cierra con Esc/Volver o al llegar al final y pulsar
    Volver otra vez."""

    # Cada página: (title_key, [body_keys...]). Los body_keys se
    # traducen y envuelven en tiempo de dibujo -- así cambiar de idioma
    # a mitad de lectura (Ajustes es accesible desde el menú, no desde
    # aquí, pero por si el idioma cambió justo antes de abrir esto) se
    # refleja sin tener que reconstruir nada.
    PAGES: list[tuple[str, list[str]]] = [
        ("tutorial.page1_title", ["tutorial.page1_body1", "tutorial.page1_body2", "tutorial.page1_body3"]),
        ("tutorial.page2_title", ["tutorial.page2_body1", "tutorial.page2_body2",
                                   "tutorial.page2_body3", "tutorial.page2_body4"]),
        ("tutorial.page3_title", ["tutorial.page3_hit", "tutorial.page3_stand", "tutorial.page3_double",
                                   "tutorial.page3_split", "tutorial.page3_surrender", "tutorial.page3_insurance"]),
        ("tutorial.page4_title", ["tutorial.page4_body1", "tutorial.page4_perfect_pairs",
                                   "tutorial.page4_21plus3", "tutorial.page4_lucky_ladies",
                                   "tutorial.page4_royal_match"]),
        ("tutorial.page5_title", ["tutorial.page5_body1", "tutorial.page5_body2",
                                   "tutorial.page5_body3", "tutorial.page5_body4"]),
    ]

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.sw, self.sh = screen.get_size()
        self._done = False
        self._page = 0

        self._font_title = pygame.font.SysFont(None, 36, bold=True)
        self._font_sub   = pygame.font.SysFont(None, 26, bold=True)
        self._font_body  = pygame.font.SysFont(None, 22)
        self._font_small = pygame.font.SysFont(None, 17)

        self._back_rect = pygame.Rect(self.sw // 2 - 90, self.sh - 70, 180, 44)
        self._back_hover = False
        self._prev_rect = pygame.Rect(60, self.sh // 2 - 28, 56, 56)
        self._next_rect = pygame.Rect(self.sw - 116, self.sh // 2 - 28, 56, 56)
        self._prev_hover = False
        self._next_hover = False

    # ------------------------------------------------------------------
    def run(self) -> None:
        clock = pygame.time.Clock()
        while not self._done:
            clock.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit
                self._handle_event(event)
            self._draw()
            pygame.display.flip()

    # ------------------------------------------------------------------
    def _go_prev(self) -> None:
        if self._page > 0:
            self._page -= 1

    def _go_next(self) -> None:
        if self._page < len(self.PAGES) - 1:
            self._page += 1

    def _handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._done = True
            elif event.key in (pygame.K_LEFT, pygame.K_PAGEUP):
                self._go_prev()
            elif event.key in (pygame.K_RIGHT, pygame.K_PAGEDOWN, pygame.K_RETURN):
                if self._page == len(self.PAGES) - 1 and event.key == pygame.K_RETURN:
                    self._done = True
                else:
                    self._go_next()

        if event.type == pygame.MOUSEBUTTONDOWN:
            if self._back_rect.collidepoint(event.pos):
                self._done = True
            elif self._prev_rect.collidepoint(event.pos):
                self._go_prev()
            elif self._next_rect.collidepoint(event.pos):
                self._go_next()

        if event.type == pygame.MOUSEMOTION:
            self._back_hover = self._back_rect.collidepoint(event.pos)
            self._prev_hover = self._prev_rect.collidepoint(event.pos)
            self._next_hover = self._next_rect.collidepoint(event.pos)

    # ------------------------------------------------------------------
    def _draw(self) -> None:
        surf = self.screen
        surf.fill(cfg.COLOR_BG)

        title = self._font_title.render(i18n.t("tutorial.title"), True, cfg.COLOR_GOLD)
        surf.blit(title, (self.sw // 2 - title.get_width() // 2, 36))

        pygame.draw.line(surf, (80, 80, 80), (self.sw // 2 - 260, 86), (self.sw // 2 + 260, 86), 1)

        title_key, body_keys = self.PAGES[self._page]
        page_title = self._font_sub.render(i18n.t(title_key), True, cfg.COLOR_TEXT)
        surf.blit(page_title, (self.sw // 2 - page_title.get_width() // 2, 106))

        max_w = 620
        y = 160
        for key in body_keys:
            text = i18n.t(key)
            for line in _wrap_text(self._font_body, text, max_w):
                rendered = self._font_body.render(line, True, (210, 210, 210))
                surf.blit(rendered, (self.sw // 2 - max_w // 2, y))
                y += rendered.get_height() + 4
            y += 14   # separación entre puntos

        # Indicador de página ("Página N de M")
        page_lbl = self._font_small.render(
            i18n.t("tutorial.page_label", n=self._page + 1, total=len(self.PAGES)),
            True, (150, 150, 150))
        surf.blit(page_lbl, (self.sw // 2 - page_lbl.get_width() // 2, self.sh - 110))

        # Puntos de paginación
        dot_r = 4
        gap = 16
        total_w = (len(self.PAGES) - 1) * gap
        dx = self.sw // 2 - total_w // 2
        for i in range(len(self.PAGES)):
            col = cfg.COLOR_GOLD if i == self._page else (90, 90, 90)
            pygame.draw.circle(surf, col, (dx + i * gap, self.sh - 90), dot_r)

        # Flechas prev/next (ocultas/atenuadas en los extremos)
        if self._page > 0:
            col = cfg.COLOR_GOLD if self._prev_hover else (140, 140, 140)
            pygame.draw.rect(surf, (20, 15, 0), self._prev_rect, border_radius=10)
            pygame.draw.rect(surf, col, self._prev_rect, 1, border_radius=10)
            icons.triangle_left(surf, self._prev_rect.centerx + 4, self._prev_rect.centery, 12, col)
        if self._page < len(self.PAGES) - 1:
            col = cfg.COLOR_GOLD if self._next_hover else (140, 140, 140)
            pygame.draw.rect(surf, (20, 15, 0), self._next_rect, border_radius=10)
            pygame.draw.rect(surf, col, self._next_rect, 1, border_radius=10)
            icons.triangle_right(surf, self._next_rect.centerx - 4, self._next_rect.centery, 12, col)

        # Botón Volver
        back_col = cfg.COLOR_GOLD if self._back_hover else (160, 130, 40)
        pygame.draw.rect(surf, (20, 15, 0), self._back_rect, border_radius=10)
        pygame.draw.rect(surf, back_col, self._back_rect, 2, border_radius=10)
        back_txt = self._font_sub.render(i18n.t("tutorial.back_button"), True, back_col)
        surf.blit(back_txt, (self._back_rect.centerx - back_txt.get_width() // 2,
                              self._back_rect.centery - back_txt.get_height() // 2))

        # Pista de teclado/ratón
        hint = self._font_small.render(i18n.t("tutorial.hint"), True, (120, 120, 120))
        surf.blit(hint, (self.sw // 2 - hint.get_width() // 2, self.sh - 26))
