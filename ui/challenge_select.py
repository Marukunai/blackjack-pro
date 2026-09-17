# ui/challenge_select.py
# Fase 25: pantalla de selección de Desafío -- lista el catálogo de
# engine.challenges, muestra el detalle del seleccionado, y devuelve el
# Challenge elegido al confirmar (o None si se cancela). Mismo patrón de
# bucle bloqueante que RulesEditor/LeaderboardScreen.
# -------------------------------------------------------------
from __future__ import annotations

import pygame
from typing import Optional

from config import settings as cfg
from config import i18n
from engine.challenges import CHALLENGES, Challenge
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


class ChallengeSelect:
    """Pantalla para elegir un Desafío antes de arrancar la partida --
    se abre desde MainMenu ("Desafíos"). Bucle bloqueante que devuelve el
    Challenge elegido al confirmar, o None si se cancela (ESC / Volver)."""

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.sw, self.sh = screen.get_size()
        self._done = False
        self._confirmed = False
        self._idx = 0

        self._font_title = pygame.font.SysFont(None, 40, bold=True)
        self._font_item  = pygame.font.SysFont(None, 24, bold=True)
        self._font_body  = pygame.font.SysFont(None, 19)
        self._font_small = pygame.font.SysFont(None, 17)

        item_w, item_h, gap = 640, 56, 10
        start_y = 100
        self._item_rects: list[pygame.Rect] = []
        for i in range(len(CHALLENGES)):
            y = start_y + i * (item_h + gap)
            self._item_rects.append(
                pygame.Rect(self.sw // 2 - item_w // 2, y, item_w, item_h))
        self._item_hover = [False] * len(CHALLENGES)

        self._detail_rect = pygame.Rect(
            self.sw // 2 - 320, start_y + len(CHALLENGES) * (item_h + gap) + 14, 640, 190)

        self._start_rect = pygame.Rect(self.sw // 2 + 20, self.sh - 74, 240, 48)
        self._back_rect  = pygame.Rect(self.sw // 2 - 260, self.sh - 74, 220, 48)
        self._start_hover = self._back_hover = False

    # ------------------------------------------------------------------
    def run(self) -> Optional[Challenge]:
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
        return CHALLENGES[self._idx] if self._confirmed else None

    def _handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._done = True
                self._confirmed = False
            elif event.key == pygame.K_RETURN:
                self._done = True
                self._confirmed = True
            elif event.key == pygame.K_UP:
                self._idx = max(0, self._idx - 1)
            elif event.key == pygame.K_DOWN:
                self._idx = min(len(CHALLENGES) - 1, self._idx + 1)

        if event.type == pygame.MOUSEMOTION:
            self._start_hover = self._start_rect.collidepoint(event.pos)
            self._back_hover = self._back_rect.collidepoint(event.pos)
            for i, r in enumerate(self._item_rects):
                self._item_hover[i] = r.collidepoint(event.pos)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._start_rect.collidepoint(event.pos):
                self._done = True
                self._confirmed = True
                return
            if self._back_rect.collidepoint(event.pos):
                self._done = True
                self._confirmed = False
                return
            for i, r in enumerate(self._item_rects):
                if r.collidepoint(event.pos):
                    self._idx = i

    # ------------------------------------------------------------------
    def _draw(self) -> None:
        surf = self.screen
        surf.fill(cfg.COLOR_BG)

        title = self._font_title.render(i18n.t("challenge_select.title"), True, cfg.COLOR_GOLD)
        surf.blit(title, (self.sw // 2 - title.get_width() // 2, 30))
        sub = self._font_small.render(
            i18n.t("challenge_select.subtitle"),
            True, (150, 150, 150))
        surf.blit(sub, (self.sw // 2 - sub.get_width() // 2, 72))

        for i, (challenge, rect) in enumerate(zip(CHALLENGES, self._item_rects)):
            selected = (i == self._idx)
            hover = self._item_hover[i]
            bg = (212, 175, 55, 40) if selected else ((255, 255, 255, 18) if hover else (0, 0, 0, 0))
            border = cfg.COLOR_GOLD if selected else ((200, 200, 200) if hover else (100, 100, 100))
            box = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            pygame.draw.rect(box, bg, box.get_rect(), border_radius=10)
            pygame.draw.rect(box, border, box.get_rect(), 1, border_radius=10)
            surf.blit(box, (rect.x, rect.y))

            icon_cx, icon_cy = rect.x + 30, rect.centery
            icons.draw_suit(surf, challenge.icon, icon_cx, icon_cy, 22, challenge.color)

            challenge_name, _challenge_desc = i18n.challenge_text(challenge)
            name_col = cfg.COLOR_GOLD if selected else cfg.COLOR_TEXT
            name_s = self._font_item.render(challenge_name, True, name_col)
            surf.blit(name_s, (rect.x + 56, rect.centery - name_s.get_height() // 2))

            facts = i18n.t("challenge_select.item_facts", limit=challenge.hand_limit,
                            chips=int(challenge.starting_chips))
            facts_s = self._font_small.render(facts, True, (150, 150, 150))
            surf.blit(facts_s, (rect.right - facts_s.get_width() - 16,
                                 rect.centery - facts_s.get_height() // 2))

        # Panel de detalle del desafío seleccionado
        dr = self._detail_rect
        panel = pygame.Surface((dr.w, dr.h), pygame.SRCALPHA)
        pygame.draw.rect(panel, (10, 10, 10, 180), panel.get_rect(), border_radius=10)
        pygame.draw.rect(panel, cfg.COLOR_GOLD, panel.get_rect(), 1, border_radius=10)
        surf.blit(panel, (dr.x, dr.y))

        chosen = CHALLENGES[self._idx]
        _chosen_name, chosen_desc = i18n.challenge_text(chosen)
        cy = dr.y + 16
        desc_lines = _wrap_text(self._font_body, chosen_desc, dr.w - 32)
        for line in desc_lines:
            ls = self._font_body.render(line, True, cfg.COLOR_TEXT)
            surf.blit(ls, (dr.x + 16, cy))
            cy += ls.get_height() + 4

        cy += 8
        detail_lines = [
            i18n.t("challenge_select.detail_hand_limit", limit=chosen.hand_limit),
            i18n.t("challenge_select.detail_starting_chips", chips=int(chosen.starting_chips)),
            i18n.t("challenge_select.detail_bet_range", min=int(chosen.min_bet), max=int(chosen.max_bet)),
        ]
        if chosen.target_chips is not None:
            detail_lines.append(i18n.t("challenge_select.detail_target_chips",
                                        target=int(chosen.target_chips)))
        if chosen.target_streak is not None:
            detail_lines.append(i18n.t("challenge_select.detail_target_streak",
                                        streak=chosen.target_streak))
        if chosen.fail_on_any_loss:
            detail_lines.append(i18n.t("challenge_select.detail_fail_on_loss"))
        if chosen.require_profit:
            detail_lines.append(i18n.t("challenge_select.detail_require_profit"))
        for line in detail_lines:
            ls = self._font_small.render(line, True, (170, 170, 170))
            surf.blit(ls, (dr.x + 16, cy))
            cy += ls.get_height() + 3

        # Botones Volver / Empezar Desafío
        back_col = cfg.COLOR_TEXT if self._back_hover else (150, 150, 150)
        pygame.draw.rect(surf, (20, 15, 0), self._back_rect, border_radius=10)
        pygame.draw.rect(surf, back_col, self._back_rect, 2, border_radius=10)
        back_txt = self._font_item.render(i18n.t("challenge_select.back_button"), True, back_col)
        surf.blit(back_txt, (self._back_rect.centerx - back_txt.get_width() // 2,
                              self._back_rect.centery - back_txt.get_height() // 2))

        start_col = cfg.COLOR_GOLD if self._start_hover else (160, 130, 40)
        pygame.draw.rect(surf, (20, 15, 0), self._start_rect, border_radius=10)
        pygame.draw.rect(surf, start_col, self._start_rect, 2, border_radius=10)
        start_txt = self._font_item.render(i18n.t("challenge_select.start_button"), True, start_col)
        surf.blit(start_txt, (self._start_rect.centerx - start_txt.get_width() // 2,
                               self._start_rect.centery - start_txt.get_height() // 2))

        hint = self._font_small.render(
            i18n.t("challenge_select.hint"),
            True, (110, 110, 110))
        surf.blit(hint, (self.sw // 2 - hint.get_width() // 2, self.sh - 24))
