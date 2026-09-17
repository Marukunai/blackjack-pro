# ui/table.py
# Mesa de casino: fieltro, zonas de cartas, decoraciones.
# -------------------------------------------------------------
from __future__ import annotations

import math
import pygame
from config import settings as cfg
from config import i18n
from ui import icons


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

    def invalidate(self) -> None:
        """Fuerza a reconstruir el fondo de la mesa en el próximo dibujo
        -- se usa al cambiar de tema de mesa en caliente desde el menú
        (ver ui/settings_screen.py), ya que el fondo se cachea tras la
        primera vez que se construye."""
        self._bg = None

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

        # Silueta minimalista del crupier, detrás de su zona de cartas
        self._draw_dealer_silhouette(surf)

        # Semicírculo decorativo del crupier
        arc_rect = pygame.Rect(sw // 2 - 120, self.dealer_zone_y - 20, 240, 60)
        pygame.draw.arc(surf, cfg.COLOR_GOLD, arc_rect, 0, math.pi, 2)

        # Marco dorado interior del fieltro
        inner = pygame.Rect(30, 18, sw - 60, sh - 36)
        pygame.draw.rect(surf, cfg.COLOR_GOLD, inner, 1, border_radius=20)

        # Logo/título centrado
        self._draw_logo(surf)

        return surf

    def _draw_dealer_silhouette(self, surf: pygame.Surface) -> None:
        """
        Presencia sutil del crupier: silueta abstracta (torso + cabeza)
        en sombra, apenas insinuada detrás de su zona de cartas, para que
        la mesa no se sienta vacía sin intentar dibujar una figura realista.
        """
        cx = self.sw // 2
        base_y = self.dealer_zone_y - 34

        silhouette = pygame.Surface((220, 130), pygame.SRCALPHA)
        col = (0, 0, 0, 70)

        # Hombros / torso (trapecio suave)
        torso = [
            (60, 130), (160, 130),
            (140, 55), (80, 55),
        ]
        pygame.draw.polygon(silhouette, col, torso)
        # Cuello
        pygame.draw.rect(silhouette, col, pygame.Rect(102, 42, 16, 20), border_radius=4)
        # Cabeza
        pygame.draw.circle(silhouette, col, (110, 30), 22)

        # Halo tenue dorado por detrás, como luz de foco cenital
        glow = pygame.Surface((260, 160), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (*cfg.COLOR_GOLD[:3], 18), glow.get_rect())
        surf.blit(glow, (cx - 130, base_y - 40))
        surf.blit(silhouette, (cx - 110, base_y - 20))

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

    @staticmethod
    def _fan_spacing(max_spacing: int, hand_w: int, total_cards: int) -> float:
        """Espaciado entre cartas: el habitual mientras quepan holgadas: en
        cuanto una mano crece (varias hits) y no cabrían con ese espaciado
        en el ancho disponible, se solapan progresivamente — el efecto
        abanico natural de una mano con muchas cartas."""
        if total_cards <= 1:
            return float(max_spacing)
        needed = (total_cards - 1) * max_spacing + cfg.CARD_WIDTH
        if needed <= hand_w:
            return float(max_spacing)
        return max(cfg.CARD_WIDTH * 0.34, (hand_w - cfg.CARD_WIDTH) / (total_cards - 1))

    @staticmethod
    def _fan_rotation(card_index: int, total_cards: int,
                       deg_per_card: float = 3.4, y_per_card: float = 2.6) -> tuple[float, int]:
        """(rotación en grados, desplazamiento Y en px) para el efecto
        abanico: sin efecto con 1-2 cartas; a partir de la 3ª, las cartas
        se inclinan levemente hacia afuera desde el centro de la mano."""
        if total_cards <= 2:
            return 0.0, 0
        mid = (total_cards - 1) / 2
        offset = card_index - mid
        rot = offset * deg_per_card
        y = int(abs(offset) * y_per_card)
        return rot, y

    def get_dealer_card_x(self, card_index: int, total_cards: int) -> int:
        """Posición X de la carta index-ésima del crupier."""
        max_spacing = min(cfg.CARD_WIDTH + 12, int(self.sw * 0.11))
        hand_w = int(self.sw * 0.7)
        spacing = self._fan_spacing(max_spacing, hand_w, total_cards)
        total_w = (total_cards - 1) * spacing + cfg.CARD_WIDTH
        start_x = self.sw // 2 - total_w // 2
        return int(start_x + card_index * spacing)

    def get_dealer_card_fan(self, card_index: int, total_cards: int) -> tuple[float, int]:
        return self._fan_rotation(card_index, total_cards)

    def get_player_card_x(self, card_index: int, total_cards: int, hand_index: int = 0, num_hands: int = 1) -> int:
        """Posición X de la carta de una mano del jugador (con soporte de splits)."""
        hand_w  = min(self.sw // num_hands - 20, int(self.sw * 0.55))
        max_spacing = min(cfg.CARD_WIDTH + 10, int(hand_w * 0.55))
        spacing = self._fan_spacing(max_spacing, hand_w, total_cards)

        hand_total_w = (total_cards - 1) * spacing + cfg.CARD_WIDTH

        if num_hands == 1:
            cx = self.sw // 2
        else:
            section_w = self.sw // num_hands
            cx = section_w * hand_index + section_w // 2

        start_x = cx - hand_total_w // 2
        return int(start_x + card_index * spacing)

    def get_player_card_fan(self, card_index: int, total_cards: int) -> tuple[float, int]:
        return self._fan_rotation(card_index, total_cards)

    def get_dealer_card_y(self) -> int:
        return self.dealer_zone_y

    def get_player_card_y(self) -> int:
        return self.player_zone_y

    def get_chip_counter_pos(self) -> tuple[int, int]:
        """Posición del icono de fichas del jugador (HUD inferior izquierdo)
        — destino del vuelo de fichas cuando el jugador gana la mano."""
        self._ensure()
        coin_r = 10
        coin_cy = self.sh - 30 + self._font_label.get_height() // 2
        return (36 + coin_r, coin_cy)

    def get_house_pos(self) -> tuple[int, int]:
        """Punto de la 'casa' hacia el que vuelan las fichas cuando el
        jugador pierde la mano (zona del crupier)."""
        return (self.sw // 2, self.dealer_zone_y - 6)

    def draw_labels(self, surf: pygame.Surface, dealer_value: str,
                    player_hands_info: list[tuple[str, bool]],
                    chips: int, bet: int, rules_str: str,
                    deck_info: str) -> None:
        """Dibuja etiquetas de valor, fichas y reglas sobre la mesa."""
        self._ensure()

        # Etiqueta crupier
        d_label = self._font_label.render(i18n.t("table.dealer_label", value=dealer_value), True, cfg.COLOR_TEXT)
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
            label_text = i18n.t("table.hand_label", value=val_str)
            col = cfg.COLOR_GOLD if active else cfg.COLOR_TEXT
            lbl = self._font_label.render(label_text, True, col)
            lx = cx - lbl.get_width() // 2
            ly = self.player_zone_y - 22
            surf.blit(lbl, (lx, ly))
            if active:
                icons.triangle_right(surf, lx - 14, ly + lbl.get_height() // 2, 9, cfg.COLOR_GOLD)

        # HUD inferior izquierdo: ficha con "$" en vez del emoji de dinero
        coin_r = 10
        coin_x, coin_cy = self.get_chip_counter_pos()
        icons.coin(surf, coin_x, coin_cy, coin_r, cfg.COLOR_GOLD, (30, 22, 0), self._font_rules)
        chip_text = self._font_label.render(f" {chips}", True, cfg.COLOR_GOLD)
        surf.blit(chip_text, (36 + coin_r * 2 + 4, self.sh - 30))

        if bet > 0:
            bet_text = self._font_rules.render(i18n.t("table.bet_label", bet=bet), True, cfg.COLOR_TEXT)
            surf.blit(bet_text, (36, self.sh - 50))

        # HUD inferior derecho
        rules_surf = self._font_rules.render(rules_str, True,
                                              tuple(min(255, c + 30) for c in cfg.COLOR_FELT_LIGHT))
        surf.blit(rules_surf, (self.sw - rules_surf.get_width() - 36, self.sh - 50))

        deck_surf = self._font_rules.render(deck_info, True,
                                             tuple(min(255, c + 30) for c in cfg.COLOR_FELT_LIGHT))
        surf.blit(deck_surf, (self.sw - deck_surf.get_width() - 36, self.sh - 30))