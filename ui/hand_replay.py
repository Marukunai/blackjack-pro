# ui/hand_replay.py
# Repetición visual de una mano concreta del historial (Fase 20).
#
# Cada fila de hand_history corresponde a UNA mano ya terminada (incluidas
# las manos individuales de un split, que se registran cada una por
# separado -- ver engine/statistics.py) y, desde esta fase, guarda también
# sus cartas (jugador + crupier) como JSON en la columna replay_data. Esta
# pantalla reconstruye esas cartas y las reparte de nuevo con las mismas
# animaciones que la partida real (reutiliza Table/CardGenerator/
# CardSprite tal cual los usa ui/renderer.py), a un ritmo fijo, y termina
# mostrando el resultado -- sin depender de un GameEngine real, ya que la
# mano ya está resuelta de antemano.
# -------------------------------------------------------------
from __future__ import annotations

import json
import time
import pygame
from typing import Optional

from config import settings as cfg
from config import i18n
from core.card import Card
from core.hand import Hand
from ui import icons
from ui.card_generator import CardGenerator
from ui.card_sprite import CardSprite
from ui.table import Table
from ui.hand_history import _RESULT_LABELS, _RESULT_COLORS

DEAL_INTERVAL = 16   # frames entre cada carta repartida (60fps ~= 0.27s)


class HandReplayScreen:
    """Bucle bloqueante de solo lectura: reparte de nuevo una mano ya
    jugada y muestra su resultado. Volver/Esc cierra sin devolver nada."""

    def __init__(self, screen: pygame.Surface, row: dict) -> None:
        self.screen = screen
        self.sw, self.sh = screen.get_size()
        self.row = row
        self._done = False

        self._font_title = pygame.font.SysFont(None, 30, bold=True)
        self._font_info  = pygame.font.SysFont(None, 20)
        self._font_small = pygame.font.SysFont(None, 16)
        self._font_result = pygame.font.SysFont(None, 44, bold=True)

        self._back_rect = pygame.Rect(self.sw // 2 - 90, self.sh - 78, 180, 44)
        self._back_hover = False

        self._error: Optional[str] = None
        self.player_cards: list[Card] = []
        self.dealer_cards: list[Card] = []
        self.is_doubled = False
        self.is_split = False
        self.surrendered = False
        self._parse_replay_data()

        self.table = Table(self.sw, self.sh)
        self.card_gen = CardGenerator()

        self._dealer_sprites: list[CardSprite] = []
        self._player_sprites: list[CardSprite] = []
        self._deal_queue: list[tuple[str, Card]] = []
        self._deal_timer = 0
        self._result_shown = False
        self._build_deal_queue()

    # ------------------------------------------------------------------
    def _parse_replay_data(self) -> None:
        raw = self.row.get("replay_data")
        if not raw:
            self._error = i18n.t("replay.no_data")
            return
        try:
            data = json.loads(raw)
            self.player_cards = [Card(c["rank"], c["suit"]) for c in data["player_cards"]]
            self.dealer_cards = [Card(c["rank"], c["suit"]) for c in data["dealer_cards"]]
            self.is_doubled = bool(data.get("is_doubled"))
            self.is_split = bool(data.get("is_split"))
            self.surrendered = bool(data.get("surrendered"))
            if not self.player_cards or not self.dealer_cards:
                raise ValueError("faltan cartas")
        except (json.JSONDecodeError, KeyError, ValueError, TypeError):
            self._error = i18n.t("replay.parse_error")

    def _build_deal_queue(self) -> None:
        if self._error:
            return
        # Orden aproximado del reparto real: las 2 primeras cartas de cada
        # uno (como en el reparto inicial), luego el resto del jugador
        # (hits/double), y por último el resto del crupier (su turno).
        pc, dc = self.player_cards, self.dealer_cards
        seq: list[tuple[str, Card]] = []
        for c in pc[:2]:
            seq.append(("player", c))
        for c in dc[:2]:
            seq.append(("dealer", c))
        for c in pc[2:]:
            seq.append(("player", c))
        for c in dc[2:]:
            seq.append(("dealer", c))
        self._deal_queue = seq

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
            self._update()
            self._draw()
            pygame.display.flip()

    def _handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE, pygame.K_RETURN):
            self._done = True
        if event.type == pygame.MOUSEMOTION:
            self._back_hover = self._back_rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._back_rect.collidepoint(event.pos):
                self._done = True

    # ------------------------------------------------------------------
    def _update(self) -> None:
        for s in self._dealer_sprites:
            s.update()
        for s in self._player_sprites:
            s.update()

        if self._deal_queue:
            self._deal_timer -= 1
            if self._deal_timer <= 0:
                self._deal_timer = DEAL_INTERVAL
                target, card = self._deal_queue.pop(0)
                self._spawn_card(target, card)

    def _spawn_card(self, target: str, card: Card) -> None:
        if target == "dealer":
            idx = len(self._dealer_sprites)
            tx = self.table.get_dealer_card_x(idx, idx + 1)
            rot, dy = self.table.get_dealer_card_fan(idx, idx + 1)
            ty = self.table.get_dealer_card_y() + dy
            sprite = CardSprite(
                card, self.card_gen, target_x=tx, target_y=ty,
                start_x=self.sw // 2, start_y=-cfg.CARD_HEIGHT, fan_rotation=rot,
            )
            self._dealer_sprites.append(sprite)
            total = len(self._dealer_sprites)
            for i, s in enumerate(self._dealer_sprites):
                nx = self.table.get_dealer_card_x(i, total)
                nrot, ndy = self.table.get_dealer_card_fan(i, total)
                ny = self.table.get_dealer_card_y() + ndy
                s.set_fan_rotation(nrot)
                if abs(s.target_x - nx) > 2 or abs(s.target_y - ny) > 2:
                    s.move_to(nx, ny, fan_rotation=nrot)
        else:
            idx = len(self._player_sprites)
            tx = self.table.get_player_card_x(idx, idx + 1, 0, 1)
            rot, dy = self.table.get_player_card_fan(idx, idx + 1)
            ty = self.table.get_player_card_y() + dy
            sprite = CardSprite(
                card, self.card_gen, target_x=tx, target_y=ty,
                start_x=self.sw // 2, start_y=self.sh + cfg.CARD_HEIGHT, fan_rotation=rot,
            )
            self._player_sprites.append(sprite)
            total = len(self._player_sprites)
            for i, s in enumerate(self._player_sprites):
                nx = self.table.get_player_card_x(i, total, 0, 1)
                nrot, ndy = self.table.get_player_card_fan(i, total)
                ny = self.table.get_player_card_y() + ndy
                s.set_fan_rotation(nrot)
                if abs(s.target_x - nx) > 2 or abs(s.target_y - ny) > 2:
                    s.move_to(nx, ny, fan_rotation=nrot)

    @property
    def _fully_dealt(self) -> bool:
        return not self._deal_queue and not any(s.is_animating for s in
                                                  self._dealer_sprites + self._player_sprites)

    # ------------------------------------------------------------------
    def _draw(self) -> None:
        surf = self.screen
        if self._error:
            self._draw_error(surf)
            self._draw_back(surf)
            return

        self.table.draw(surf)

        for s in self._dealer_sprites:
            s.draw(surf)
        for s in self._player_sprites:
            s.draw(surf)

        self._draw_values(surf)
        self._draw_info_bar(surf)
        if self._fully_dealt:
            self._draw_result(surf)
        self._draw_back(surf)

    def _draw_error(self, surf: pygame.Surface) -> None:
        surf.fill(cfg.COLOR_BG)
        t = self._font_info.render(self._error, True, (200, 80, 80))
        surf.blit(t, (self.sw // 2 - t.get_width() // 2, self.sh // 2 - 20))

    def _draw_values(self, surf: pygame.Surface) -> None:
        dealer_hand = Hand()
        for c in self._dealt_cards("dealer"):
            dealer_hand.add_card(c)
        d_label = (i18n.t("replay.dealer_label_value", value=dealer_hand.value)
                   if dealer_hand.cards else i18n.t("replay.dealer_label_empty"))
        d_surf = self._font_info.render(d_label, True, cfg.COLOR_TEXT)
        surf.blit(d_surf, (self.sw // 2 - d_surf.get_width() // 2, self.table.dealer_zone_y - 24))

        player_hand = Hand()
        for c in self._dealt_cards("player"):
            player_hand.add_card(c)
        tags = []
        if self.is_doubled:
            tags.append(i18n.t("replay.tag_doubled"))
        if self.surrendered:
            tags.append(i18n.t("replay.tag_surrendered"))
        tag_str = f" ({', '.join(tags)})" if tags else ""
        p_label = (i18n.t("replay.player_label_value", value=player_hand.value, tags=tag_str)
                   if player_hand.cards else i18n.t("replay.player_label_empty"))
        p_surf = self._font_info.render(p_label, True, cfg.COLOR_GOLD)
        surf.blit(p_surf, (self.sw // 2 - p_surf.get_width() // 2, self.table.player_zone_y - 24))

    def _dealt_cards(self, target: str) -> list[Card]:
        sprites = self._dealer_sprites if target == "dealer" else self._player_sprites
        return [s.card for s in sprites]

    def _draw_info_bar(self, surf: pygame.Surface) -> None:
        row = self.row
        try:
            date_str = time.strftime("%d/%m/%Y %H:%M", time.localtime(row["played_at"]))
        except (OSError, ValueError, KeyError):
            date_str = "—"
        preset = i18n.preset_label(row.get("preset_name") or "—")
        text = i18n.t("replay.info_bar", date=date_str, preset=preset, bet=row.get('bet', 0))
        t = self._font_small.render(text, True, (140, 140, 140))
        surf.blit(t, (self.sw // 2 - t.get_width() // 2, 18))

    def _draw_result(self, surf: pygame.Surface) -> None:
        result_key = self.row.get("result", "")
        label = _RESULT_LABELS.get(result_key, result_key)
        color = _RESULT_COLORS.get(result_key, cfg.COLOR_TEXT)
        net = self.row.get("net", 0.0)

        text = f"{label}  ({net:+.0f})"
        s = self._font_result.render(text, True, color)
        y = self.table.get_player_card_y() + cfg.CARD_HEIGHT + 34
        box = pygame.Surface((s.get_width() + 32, s.get_height() + 20), pygame.SRCALPHA)
        pygame.draw.rect(box, (0, 0, 0, 150), box.get_rect(), border_radius=10)
        pygame.draw.rect(box, (*color, 180), box.get_rect(), 2, border_radius=10)
        bx = self.sw // 2 - box.get_width() // 2
        surf.blit(box, (bx, y))
        surf.blit(s, (self.sw // 2 - s.get_width() // 2, y + 10))

    def _draw_back(self, surf: pygame.Surface) -> None:
        back_col = cfg.COLOR_GOLD if self._back_hover else (150, 150, 150)
        pygame.draw.rect(surf, (20, 15, 0), self._back_rect, border_radius=10)
        pygame.draw.rect(surf, back_col, self._back_rect, 2, border_radius=10)
        back_txt = self._font_info.render(i18n.t("replay.back_button"), True, back_col)
        surf.blit(back_txt, (self._back_rect.centerx - back_txt.get_width() // 2,
                              self._back_rect.centery - back_txt.get_height() // 2))
        hint = self._font_small.render(i18n.t("replay.exit_hint"), True, (90, 90, 90))
        surf.blit(hint, (self.sw // 2 - hint.get_width() // 2, self.sh - 24))
