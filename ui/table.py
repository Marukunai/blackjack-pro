# ui/table.py
# Mesa de casino: fieltro, zonas de cartas, decoraciones.
# -------------------------------------------------------------
from __future__ import annotations

import math
import pygame
from config import settings as cfg


class Table:
    """
    Dibuja el fondo de la mesa: fieltro verde, semicírculo del crupier,
    línea divisoria y etiquetas de zona.
    """

    def __init__(self, screen_w: int, screen_h: int) -> None:
        self.sw = screen_w
        self.sh = screen_h

        # Zonas de cartas
        self.dealer_zone_y  = int(screen_h * 0.10)
        self.player_zone_y  = int(screen_h * 0.52)
        self.bet_zone_y     = int(screen_h * 0.42)
        self.divider_y      = int(screen_h * 0.46)

        self._bg: pygame.Surface | None = None
        self._font_label: pygame.font.Font | None = None
        self._font_rules: pygame.font.Font | None = None

    def _ensure(self) -> None:
        if self._bg is not None:
            return
        self._font_label = pygame.font.SysFont(None, 22, bold=True)
        self._font_rules = pygame.font.SysFont(None, 17)
        self._bg = self._build_bg()

    def _build_bg(self) -> pygame.Surface:
        sw, sh = self.sw, self.sh
        surf = pygame.Surface((sw, sh))

        # Fondo oscuro
        surf.fill(cfg.COLOR_BG)

        # Fieltro principal
        felt_rect = pygame.Rect(20, 10, sw - 40, sh - 20)
        pygame.draw.rect(surf, cfg.COLOR_FELT, felt_rect, border_radius=24)

        # Textura de fieltro (punteado sutil)
        self._draw_felt_texture(surf, felt_rect)

        # Línea divisoria central (zona jugador/crupier)
        pygame.draw.line(surf, cfg.COLOR_FELT_LIGHT,
                         (60, self.divider_y), (sw - 60, self.divider_y), 2)

        # Semicírculo decorativo del crupier
        arc_rect = pygame.Rect(sw // 2 - 120, self.dealer_zone_y - 20, 240, 60)
        pygame.draw.arc(surf, cfg.COLOR_GOLD, arc_rect, 0, math.pi, 2)

        # Marco dorado interior del fieltro
        inner = pygame.Rect(30, 18, sw - 60, sh - 36)
        pygame.draw.rect(surf, cfg.COLOR_GOLD, inner, 1, border_radius=20)

        # Logo/título centrado
        self._draw_logo(surf)

        return surf

    def _draw_felt_texture(self, surf: pygame.Surface, rect: pygame.Rect) -> None:
        """Punteado sutil para simular textura de fieltro."""
        col = tuple(min(255, c + 8) for c in cfg.COLOR_FELT)
        step = 14
        for x in range(rect.left + 7, rect.right, step):
            for y in range(rect.top + 7, rect.bottom, step):
                if rect.collidepoint(x, y):
                    pygame.draw.circle(surf, col, (x, y), 1)

    def _draw_logo(self, surf: pygame.Surface) -> None:
        """Texto central decorativo de la mesa."""
        font = pygame.font.SysFont(None, 28, bold=True)
        text = font.render("BLACKJACK  PAYS  3 : 2", True, cfg.COLOR_GOLD)
        x = self.sw // 2 - text.get_width() // 2
        y = self.divider_y - text.get_height() - 8
        # Sombra
        shadow = font.render("BLACKJACK  PAYS  3 : 2", True, (0, 0, 0))
        surf.blit(shadow, (x+1, y+1))
        surf.blit(text, (x, y))

        font2 = pygame.font.SysFont(None, 17)
        sub = font2.render("DEALER MUST STAND ON ALL 17s", True,
                           tuple(min(255, c + 40) for c in cfg.COLOR_FELT_LIGHT))
        surf.blit(sub, (self.sw//2 - sub.get_width()//2, y + text.get_height() + 2))

    def draw(self, surf: pygame.Surface) -> None:
        self._ensure()
        surf.blit(self._bg, (0, 0))

    def get_dealer_card_x(self, card_index: int, total_cards: int) -> int:
        """Posición X de la carta index-ésima del crupier."""
        spacing = min(cfg.CARD_WIDTH + 12, int(self.sw * 0.11))
        total_w = total_cards * cfg.CARD_WIDTH + (total_cards - 1) * (spacing - cfg.CARD_WIDTH)
        start_x = self.sw // 2 - total_w // 2
        return start_x + card_index * spacing

    def get_player_card_x(self, card_index: int, total_cards: int, hand_index: int = 0, num_hands: int = 1) -> int:
        """Posición X de la carta de una mano del jugador (con soporte de splits)."""
        hand_w  = min(self.sw // num_hands - 20, int(self.sw * 0.55))
        spacing = min(cfg.CARD_WIDTH + 10, int(hand_w * 0.55))

        hand_total_w = total_cards * cfg.CARD_WIDTH + (total_cards - 1) * (spacing - cfg.CARD_WIDTH)

        if num_hands == 1:
            cx = self.sw // 2
        else:
            section_w = self.sw // num_hands
            cx = section_w * hand_index + section_w // 2

        start_x = cx - hand_total_w // 2
        return start_x + card_index * spacing

    def get_dealer_card_y(self) -> int:
        return self.dealer_zone_y

    def get_player_card_y(self) -> int:
        return self.player_zone_y

    def draw_labels(self, surf: pygame.Surface, dealer_value: str,
                    player_hands_info: list[tuple[str, bool]],
                    chips: int, bet: int, rules_str: str,
                    deck_info: str) -> None:
        """Dibuja etiquetas de valor, fichas y reglas sobre la mesa."""
        self._ensure()

        # Etiqueta crupier
        d_label = self._font_label.render(f"CRUPIER  {dealer_value}", True, cfg.COLOR_TEXT)
        surf.blit(d_label, (self.sw // 2 - d_label.get_width() // 2,
                             self.dealer_zone_y - 22))

        # Etiquetas jugador (una por mano)
        for i, (val_str, active) in enumerate(player_hands_info):
            num_hands = len(player_hands_info)
            if num_hands == 1:
                cx = self.sw // 2
            else:
                section = self.sw // num_hands
                cx = section * i + section // 2
            label_text = f"{'► ' if active else ''}TU MANO  {val_str}"
            col = cfg.COLOR_GOLD if active else cfg.COLOR_TEXT
            lbl = self._font_label.render(label_text, True, col)
            surf.blit(lbl, (cx - lbl.get_width() // 2,
                            self.player_zone_y - 22))

        # HUD inferior izquierdo
        chip_text = self._font_label.render(f"💰 {chips}", True, cfg.COLOR_GOLD)
        surf.blit(chip_text, (36, self.sh - 30))

        if bet > 0:
            bet_text = self._font_rules.render(f"Apuesta: {bet}", True, cfg.COLOR_TEXT)
            surf.blit(bet_text, (36, self.sh - 50))

        # HUD inferior derecho
        rules_surf = self._font_rules.render(rules_str, True,
                                              tuple(min(255, c + 30) for c in cfg.COLOR_FELT_LIGHT))
        surf.blit(rules_surf, (self.sw - rules_surf.get_width() - 36, self.sh - 50))

        deck_surf = self._font_rules.render(deck_info, True,
                                             tuple(min(255, c + 30) for c in cfg.COLOR_FELT_LIGHT))
        surf.blit(deck_surf, (self.sw - deck_surf.get_width() - 36, self.sh - 30))