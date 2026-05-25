# ui/hud.py
# HUD: mensajes flotantes, hint de estrategia básica, contador Hi-Lo,
# panel de estadísticas, overlay de resultado de ronda.
# -------------------------------------------------------------
from __future__ import annotations

import pygame
from typing import Optional
from config import settings as cfg
from ai.basic_strategy import get_basic_strategy, ACTION_COLOR, BasicAction
from ai.card_counter import HiLoCounter


# Mapa de BasicAction → texto legible
ACTION_LABELS = {
    BasicAction.H:  "Hit",
    BasicAction.S:  "Stand",
    BasicAction.D:  "Double (si no, Hit)",
    BasicAction.DS: "Double (si no, Stand)",
    BasicAction.P:  "Split",
    BasicAction.PH: "Split (si no, Hit)",
    BasicAction.R:  "Surrender (si no, Hit)",
    BasicAction.RS: "Surrender (si no, Stand)",
    BasicAction.RP: "Surrender (si no, Split)",
}

# Mapa BasicAction → color RGB
ACTION_RGB = {
    BasicAction.H:  (220, 60,  60),
    BasicAction.S:  (50,  180, 80),
    BasicAction.D:  (220, 150, 0),
    BasicAction.DS: (200, 120, 0),
    BasicAction.P:  (50,  120, 220),
    BasicAction.PH: (80,  150, 230),
    BasicAction.R:  (150, 60,  200),
    BasicAction.RS: (160, 80,  210),
    BasicAction.RP: (170, 90,  220),
}


class FloatingMessage:
    """Texto que sube y desvanece."""
    LIFE = 100

    def __init__(self, text: str, x: int, y: int, color: tuple):
        self.text  = text
        self.x, self.y = float(x), float(y)
        self.color = color
        self._life = self.LIFE
        self._font = pygame.font.SysFont(None, 30, bold=True)

    def update(self) -> bool:
        self._life -= 1
        self.y -= 0.6
        return self._life > 0

    def draw(self, surf: pygame.Surface) -> None:
        alpha = int(255 * (self._life / self.LIFE))
        s = self._font.render(self.text, True, self.color)
        s.set_alpha(alpha)
        surf.blit(s, (int(self.x) - s.get_width()//2, int(self.y)))


class HUD:
    """
    Capa de interfaz superpuesta a la mesa.
    Gestiona: hints, contador Hi-Lo, mensajes flotantes,
    banner de resultado y panel de estadísticas.
    """

    def __init__(self, screen_w: int, screen_h: int) -> None:
        self.sw = screen_w
        self.sh = screen_h
        self._messages: list[FloatingMessage] = []
        self._result_banner: Optional[tuple[str, tuple, int]] = None  # text, color, timer
        self._font_hint:  Optional[pygame.font.Font] = None
        self._font_small: Optional[pygame.font.Font] = None
        self._font_big:   Optional[pygame.font.Font] = None
        self._font_stats: Optional[pygame.font.Font] = None
        self._show_stats  = False

    def _ensure_fonts(self) -> None:
        if self._font_hint:
            return
        self._font_hint  = pygame.font.SysFont(None, 20, bold=True)
        self._font_small = pygame.font.SysFont(None, 17)
        self._font_big   = pygame.font.SysFont(None, 56, bold=True)
        self._font_stats = pygame.font.SysFont(None, 19)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def add_message(self, text: str, x: int, y: int, color: tuple = cfg.COLOR_TEXT) -> None:
        self._messages.append(FloatingMessage(text, x, y, color))

    def show_result(self, text: str, color: tuple) -> None:
        self._result_banner = (text, color, 120)

    def toggle_stats(self) -> None:
        self._show_stats = not self._show_stats

    # ------------------------------------------------------------------
    # Update + Draw
    # ------------------------------------------------------------------
    def update(self) -> None:
        self._messages = [m for m in self._messages if m.update()]
        if self._result_banner:
            text, col, t = self._result_banner
            t -= 1
            self._result_banner = (text, col, t) if t > 0 else None

    def draw(self, surf: pygame.Surface,
             engine=None,
             counter: Optional[HiLoCounter] = None) -> None:
        self._ensure_fonts()

        # Mensajes flotantes
        for m in self._messages:
            m.draw(surf)

        # Banner de resultado
        if self._result_banner:
            text, col, timer = self._result_banner
            alpha = min(255, timer * 5)
            offset = max(0, (120 - timer) // 4)
            s = self._font_big.render(text, True, col)
            s.set_alpha(alpha)
            shadow = self._font_big.render(text, True, (0, 0, 0))
            shadow.set_alpha(alpha // 2)
            cx = self.sw // 2 - s.get_width() // 2
            cy = self.sh // 2 - s.get_height() // 2 - offset
            surf.blit(shadow, (cx+3, cy+3))
            surf.blit(s,      (cx,   cy))

        # Hint de estrategia básica
        if cfg.SHOW_HINTS and engine is not None:
            self._draw_hint(surf, engine)

        # Contador Hi-Lo
        if cfg.SHOW_CARD_COUNTER and counter is not None:
            self._draw_counter(surf, counter)

        # Panel de estadísticas
        if self._show_stats and engine is not None:
            self._draw_stats_panel(surf, engine)

    # ------------------------------------------------------------------
    # Sub-draws
    # ------------------------------------------------------------------
    def _draw_hint(self, surf: pygame.Surface, engine) -> None:
        from engine.game_state import GameState
        if engine.state != GameState.PLAYER_TURN:
            return
        hand = engine.player.active_hand
        if not hand or hand.is_finished:
            return
        try:
            hint = get_basic_strategy(hand, engine.dealer.upcard_value, engine.rules)
        except Exception:
            return

        label = ACTION_LABELS.get(hint, hint.value)
        color = ACTION_RGB.get(hint, (200, 200, 200))

        # Caja de hint
        padding = 8
        text_s = self._font_hint.render(f"Estrategia: {label}", True, color)
        box_w = text_s.get_width() + padding * 2
        box_h = text_s.get_height() + padding * 2
        x = self.sw - box_w - 14
        y = 14

        box = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        pygame.draw.rect(box, (0, 0, 0, 150), box.get_rect(), border_radius=6)
        pygame.draw.rect(box, (*color, 180), box.get_rect(), 2, border_radius=6)
        surf.blit(box, (x, y))
        surf.blit(text_s, (x + padding, y + padding))

    def _draw_counter(self, surf: pygame.Surface, counter: HiLoCounter) -> None:
        tc = counter.true_count_rounded
        if tc >= 2:
            col = (80, 220, 80)
        elif tc <= -2:
            col = (80, 140, 220)
        else:
            col = (200, 200, 200)

        lines = [
            f"Hi-Lo  RC: {counter.running_count:+d}",
            f"TC: {counter.true_count:+.1f}  {counter.count_label}",
        ]
        padding = 8
        line_surfs = [self._font_small.render(l, True, col) for l in lines]
        box_w = max(s.get_width() for s in line_surfs) + padding * 2
        box_h = sum(s.get_height() for s in line_surfs) + padding * 2 + 4
        x, y = 14, 14

        box = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        pygame.draw.rect(box, (0, 0, 0, 150), box.get_rect(), border_radius=6)
        pygame.draw.rect(box, (*col, 180), box.get_rect(), 2, border_radius=6)
        surf.blit(box, (x, y))
        cy = y + padding
        for s in line_surfs:
            surf.blit(s, (x + padding, cy))
            cy += s.get_height() + 2

    def _draw_stats_panel(self, surf: pygame.Surface, engine) -> None:
        s = engine.player.stats
        lines = [
            f"Jugador: {engine.player.name}",
            f"Fichas:  {int(engine.player.chips)}",
            "─" * 22,
            f"Manos:   {s.hands_played}",
            f"W / L / P: {s.hands_won} / {s.hands_lost} / {s.hands_push}",
            f"Winrate: {s.win_rate:.1%}",
            f"ROI:     {s.roi:+.1%}",
            f"Neto:    {s.net_profit:+.0f}",
            "─" * 22,
            f"Blackjacks: {s.blackjacks}",
            f"Busts:      {s.busts}",
            f"Mejor racha: +{s.best_streak}",
        ]
        padding = 10
        line_surfs = [self._font_stats.render(l, True, cfg.COLOR_TEXT) for l in lines]
        box_w = max(s.get_width() for s in line_surfs) + padding * 2
        box_h = sum(s.get_height() + 3 for s in line_surfs) + padding * 2
        x = self.sw // 2 - box_w // 2
        y = self.sh // 2 - box_h // 2

        panel = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        pygame.draw.rect(panel, (10, 10, 10, 210), panel.get_rect(), border_radius=10)
        pygame.draw.rect(panel, cfg.COLOR_GOLD, panel.get_rect(), 1, border_radius=10)
        surf.blit(panel, (x, y))
        cy = y + padding
        for ls in line_surfs:
            surf.blit(ls, (x + padding, cy))
            cy += ls.get_height() + 3