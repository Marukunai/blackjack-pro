# ui/hud.py
# HUD: mensajes flotantes, hint de estrategia básica, contador Hi-Lo,
# panel de estadísticas, overlay de resultado de ronda.
# -------------------------------------------------------------
from __future__ import annotations

import math
import pygame
from typing import Optional
from config import settings as cfg
from ui import icons
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
        self._result_banner: Optional[tuple[str, tuple, int, Optional[str]]] = None  # text, color, timer, icon
        self._font_hint:  Optional[pygame.font.Font] = None
        self._font_small: Optional[pygame.font.Font] = None
        self._font_big:   Optional[pygame.font.Font] = None
        self._font_stats: Optional[pygame.font.Font] = None
        self._show_stats  = False
        self._show_achievements = False

        # Flash del contador Hi-Lo cuando cambia el true count
        self._last_tc: Optional[int] = None
        self._tc_flash = 0
        self._TC_FLASH_FRAMES = 14

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

    def show_result(self, text: str, color: tuple, icon: Optional[str] = None) -> None:
        """icon: 'check' | 'cross' | 'star' | None — dibujado junto al texto
        en vez de depender de un glifo Unicode (✓✗★) que puede no existir
        en la fuente del sistema."""
        self._result_banner = (text, color, 120, icon)

    def toggle_stats(self) -> None:
        self._show_stats = not self._show_stats

    def toggle_achievements(self) -> None:
        self._show_achievements = not self._show_achievements

    # ------------------------------------------------------------------
    # Update + Draw
    # ------------------------------------------------------------------
    def update(self) -> None:
        self._messages = [m for m in self._messages if m.update()]
        if self._result_banner:
            text, col, t, icon = self._result_banner
            t -= 1
            self._result_banner = (text, col, t, icon) if t > 0 else None
        if self._tc_flash > 0:
            self._tc_flash -= 1

    def draw(self, surf: pygame.Surface,
             engine=None,
             counter: Optional[HiLoCounter] = None,
             unlocked_achievements: Optional[set] = None,
             training_stats: Optional[tuple] = None) -> None:
        self._ensure_fonts()

        # Mensajes flotantes
        for m in self._messages:
            m.draw(surf)

        # Banner de resultado
        if self._result_banner:
            text, col, timer, icon = self._result_banner
            alpha = min(255, timer * 5)
            offset = max(0, (120 - timer) // 4)
            s = self._font_big.render(text, True, col)
            s.set_alpha(alpha)
            shadow = self._font_big.render(text, True, (0, 0, 0))
            shadow.set_alpha(alpha // 2)

            icon_w = s.get_height() + 14 if icon else 0
            total_w = s.get_width() + icon_w
            cx = self.sw // 2 - total_w // 2
            cy = self.sh // 2 - s.get_height() // 2 - offset

            if icon:
                icon_cx = cx + s.get_height() // 2
                icon_cy = cy + s.get_height() // 2
                icon_r = s.get_height() * 0.42
                if icon == "check":
                    icons.check_mark(surf, icon_cx, icon_cy, icon_r * 1.7, col, width=4)
                elif icon == "cross":
                    icons.cross_mark(surf, icon_cx, icon_cy, icon_r * 1.7, col, width=4)
                elif icon == "star":
                    icons.star(surf, icon_cx, icon_cy, icon_r, col)

            surf.blit(shadow, (cx + icon_w + 3, cy + 3))
            surf.blit(s,      (cx + icon_w,     cy))

        # Hint de estrategia básica
        if cfg.SHOW_HINTS and engine is not None:
            self._draw_hint(surf, engine)

        # Marcador del modo entrenamiento (Fase 19)
        if cfg.TRAINING_MODE and training_stats is not None:
            self._draw_training_badge(surf, *training_stats)

        # Contador Hi-Lo
        if cfg.SHOW_CARD_COUNTER and counter is not None:
            self._draw_counter(surf, counter)

        # Panel de estadísticas
        if self._show_stats and engine is not None:
            self._draw_stats_panel(surf, engine)

        # Panel de logros
        if self._show_achievements:
            self._draw_achievements_panel(surf, unlocked_achievements or set())

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

    def _draw_training_badge(self, surf: pygame.Surface, correct: int, total: int) -> None:
        """Marcador fijo (esquina superior derecha, debajo del hint si está
        visible) con el acierto acumulado de la sesión de entrenamiento:
        cuántas jugadas han coincidido con la estrategia básica."""
        pct = (correct / total * 100) if total else 0.0
        text = f"Entrenamiento: {correct}/{total} ({pct:.0f}%)"
        color = (80, 220, 80) if (total == 0 or pct >= 80) else (
            (220, 150, 0) if pct >= 50 else (220, 60, 60))

        padding = 8
        text_s = self._font_hint.render(text, True, color)
        box_w = text_s.get_width() + padding * 2
        box_h = text_s.get_height() + padding * 2
        x = self.sw - box_w - 14
        y = 14 + (38 if cfg.SHOW_HINTS else 0)

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

        # Detectar cambio de true count → pulso breve del recuadro
        if self._last_tc is not None and tc != self._last_tc:
            self._tc_flash = self._TC_FLASH_FRAMES
        self._last_tc = tc

        lines = [
            f"Hi-Lo  RC: {counter.running_count:+d}",
            f"TC: {counter.true_count:+.1f}  {counter.count_label}",
        ]
        padding = 8
        line_surfs = [self._font_small.render(l, True, col) for l in lines]
        box_w = max(s.get_width() for s in line_surfs) + padding * 2
        box_h = sum(s.get_height() for s in line_surfs) + padding * 2 + 4
        x, y = 14, 14

        flash_t = self._tc_flash / self._TC_FLASH_FRAMES if self._tc_flash > 0 else 0.0
        border_w = 2 + int(2 * flash_t)
        bg_alpha = int(150 + 60 * flash_t)

        box = pygame.Surface((box_w + 8, box_h + 8), pygame.SRCALPHA)
        pygame.draw.rect(box, (0, 0, 0, bg_alpha), (4, 4, box_w, box_h), border_radius=6)
        pygame.draw.rect(box, (*col, min(255, 180 + int(75 * flash_t))),
                          (4, 4, box_w, box_h), border_w, border_radius=6)
        if flash_t > 0:
            glow = pygame.Surface((box_w + 8, box_h + 8), pygame.SRCALPHA)
            pygame.draw.rect(glow, (*col, int(70 * flash_t)), glow.get_rect(), border_radius=8)
            surf.blit(glow, (x - 4, y - 4))
        surf.blit(box, (x - 4, y - 4))
        cy = y + padding
        for s in line_surfs:
            surf.blit(s, (x + padding, cy))
            cy += s.get_height() + 2

    def _draw_stats_panel(self, surf: pygame.Surface, engine) -> None:
        s = engine.player.stats
        DIVIDER = None   # marcador: dibuja una línea en vez de texto
        lines = [
            f"Jugador: {engine.player.name}",
            f"Fichas:  {int(engine.player.chips)}",
            DIVIDER,
            f"Manos:   {s.hands_played}",
            f"W / L / P: {s.hands_won} / {s.hands_lost} / {s.hands_push}",
            f"Winrate: {s.win_rate:.1%}",
            f"ROI:     {s.roi:+.1%}",
            f"Neto:    {s.net_profit:+.0f}",
            DIVIDER,
            f"Blackjacks: {s.blackjacks}",
            f"Busts:      {s.busts}",
            f"Mejor racha: +{s.best_streak}",
        ]
        padding = 10
        divider_h = 9
        line_surfs = [None if l is DIVIDER else self._font_stats.render(l, True, cfg.COLOR_TEXT)
                      for l in lines]
        text_widths = [ls.get_width() for ls in line_surfs if ls is not None]
        box_w = (max(text_widths) if text_widths else 100) + padding * 2
        box_h = sum((ls.get_height() + 3) if ls is not None else divider_h
                    for ls in line_surfs) + padding * 2
        x = self.sw // 2 - box_w // 2
        y = self.sh // 2 - box_h // 2

        panel = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        pygame.draw.rect(panel, (10, 10, 10, 210), panel.get_rect(), border_radius=10)
        pygame.draw.rect(panel, cfg.COLOR_GOLD, panel.get_rect(), 1, border_radius=10)
        surf.blit(panel, (x, y))
        cy = y + padding
        for ls in line_surfs:
            if ls is None:
                icons.hline(surf, x + padding, cy + divider_h // 2,
                            box_w - padding * 2, (90, 90, 90))
                cy += divider_h
                continue
            surf.blit(ls, (x + padding, cy))
            cy += ls.get_height() + 3

    def _draw_achievements_panel(self, surf: pygame.Surface, unlocked_ids: set) -> None:
        from engine.achievements import ACHIEVEMENTS
        self._ensure_fonts()

        padding = 14
        row_h = 46
        cols = 2
        col_w = 300
        rows = (len(ACHIEVEMENTS) + cols - 1) // cols
        box_w = cols * col_w + padding * 2
        box_h = rows * row_h + padding * 2 + 30
        x = self.sw // 2 - box_w // 2
        y = self.sh // 2 - box_h // 2

        panel = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        pygame.draw.rect(panel, (10, 10, 10, 225), panel.get_rect(), border_radius=12)
        pygame.draw.rect(panel, cfg.COLOR_GOLD, panel.get_rect(), 1, border_radius=12)
        surf.blit(panel, (x, y))

        n_unlocked = len(unlocked_ids)
        title_font = pygame.font.SysFont(None, 24, bold=True)
        title = title_font.render(f"Logros  ({n_unlocked}/{len(ACHIEVEMENTS)})", True, cfg.COLOR_GOLD)
        surf.blit(title, (x + box_w // 2 - title.get_width() // 2, y + 10))

        top = y + 38
        for i, ach in enumerate(ACHIEVEMENTS):
            col, row = i % cols, i // cols
            cx0 = x + padding + col * col_w
            cy0 = top + row * row_h
            unlocked = ach.id in unlocked_ids

            icon_r = 15
            icon_cx, icon_cy = cx0 + icon_r, cy0 + row_h // 2
            if unlocked:
                color = ach.color
                bg = tuple(max(0, c - 165) for c in color)
                pygame.draw.circle(surf, bg, (icon_cx, icon_cy), icon_r)
                pygame.draw.circle(surf, color, (icon_cx, icon_cy), icon_r, 2)
                if ach.icon == "star":
                    icons.star(surf, icon_cx, icon_cy, icon_r * 0.55, color)
                elif ach.icon == "coin":
                    icons.coin(surf, icon_cx, icon_cy, icon_r * 0.6, color, (20, 20, 20), self._font_small)
                else:
                    icons.draw_suit(surf, ach.icon, icon_cx, icon_cy, icon_r * 1.1, color)
            else:
                pygame.draw.circle(surf, (24, 24, 24), (icon_cx, icon_cy), icon_r)
                pygame.draw.circle(surf, (80, 80, 80), (icon_cx, icon_cy), icon_r, 2)
                # Candado sencillo: cuerpo + arco de la anilla
                pygame.draw.rect(surf, (110, 110, 110),
                                  (icon_cx - 5, icon_cy - 2, 10, 8), border_radius=2)
                pygame.draw.arc(surf, (110, 110, 110),
                                 (icon_cx - 5, icon_cy - 9, 10, 10), 0, math.pi, 2)

            name_col = cfg.COLOR_TEXT if unlocked else (110, 110, 110)
            desc_col = (150, 150, 150) if unlocked else (75, 75, 75)
            name_s = self._font_stats.render(ach.name, True, name_col)
            desc_s = self._font_small.render(ach.description, True, desc_col)
            tx = cx0 + icon_r * 2 + 10
            surf.blit(name_s, (tx, cy0 + 2))
            surf.blit(desc_s, (tx, cy0 + 2 + name_s.get_height()))