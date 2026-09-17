# ui/hud.py
# HUD: mensajes flotantes, hint de estrategia básica, contador Hi-Lo,
# panel de estadísticas, overlay de resultado de ronda.
# -------------------------------------------------------------
from __future__ import annotations

import math
import pygame
from typing import Optional
from config import settings as cfg
from config import i18n
from ui import icons
from ai.basic_strategy import get_basic_strategy, ACTION_COLOR, BasicAction
from ai.card_counter import HiLoCounter


# Mapa de BasicAction → clave de i18n (Hit/Stand/Split son términos de
# casino que ya se dejan en inglés en los dos idiomas -- solo la parte
# "(si no, ...)" se traduce; ver ACTION_LABELS() más abajo).
_ACTION_LABEL_KEYS = {
    BasicAction.D:  "hud.action_double_or_hit",
    BasicAction.DS: "hud.action_double_or_stand",
    BasicAction.PH: "hud.action_split_or_hit",
    BasicAction.R:  "hud.action_surrender_or_hit",
    BasicAction.RS: "hud.action_surrender_or_stand",
    BasicAction.RP: "hud.action_surrender_or_split",
}
_ACTION_LABEL_PLAIN = {
    BasicAction.H: "Hit",
    BasicAction.S: "Stand",
    BasicAction.P: "Split",
}


def _action_label(action) -> str:
    if action in _ACTION_LABEL_PLAIN:
        return _ACTION_LABEL_PLAIN[action]
    key = _ACTION_LABEL_KEYS.get(action)
    return i18n.t(key) if key else action.value

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

    def clear_transient(self) -> None:
        """Descarta mensajes flotantes y el banner de resultado (GANASTE/
        PERDISTE/etc.) que todavía no hayan terminado de desvanecerse --
        para no dejarlos asomando bajo una pantalla nueva a pantalla
        completa (Game Over, fin de Desafío) que se dibuja justo encima."""
        self._messages.clear()
        self._result_banner = None

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
             training_stats: Optional[tuple] = None,
             challenge=None) -> None:
        self._ensure_fonts()

        # Banner de Desafío activo (Fase 25) -- arriba-centro, igual que
        # ocuparía la tira de asientos multijugador (con la que nunca
        # coincide: los desafíos son siempre en solitario).
        if challenge is not None and engine is not None:
            self._draw_challenge_banner(surf, challenge, engine)

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

    def _draw_challenge_banner(self, surf: pygame.Surface, challenge, engine) -> None:
        """Banner fijo arriba-centro con el progreso del Desafío activo:
        nombre, el objetivo en cifras (Challenge.progress_label) y una
        barra de progreso -- de un vistazo, sin abrir ningún panel."""
        stats = engine.player.stats
        chips = engine.player.chips
        box_w, box_h = 380, 62
        x = self.sw // 2 - box_w // 2
        y = 8

        box = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        pygame.draw.rect(box, (0, 0, 0, 150), box.get_rect(), border_radius=10)
        pygame.draw.rect(box, (*challenge.color, 220), box.get_rect(), 2, border_radius=10)
        surf.blit(box, (x, y))

        icon_cx, icon_cy = x + 24, y + box_h // 2
        icons.draw_suit(surf, challenge.icon, icon_cx, icon_cy, 20, challenge.color)

        left = x + 46
        challenge_name, _ = i18n.challenge_text(challenge)
        name_s = self._font_hint.render(challenge_name, True, challenge.color)
        surf.blit(name_s, (left, y + 6))

        hands_s = self._font_small.render(
            i18n.t("hud.challenge_hands_progress", played=stats.hands_played, limit=challenge.hand_limit),
            True, (150, 150, 150))
        surf.blit(hands_s, (x + box_w - hands_s.get_width() - 12, y + 8))

        label_s = self._font_small.render(
            challenge.progress_label(stats, chips), True, (200, 200, 200))
        surf.blit(label_s, (left, y + 26))

        bar_x, bar_y, bar_w, bar_h = left, y + 46, box_w - (left - x) - 12, 8
        pygame.draw.rect(surf, (40, 40, 40), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        frac = challenge.progress(stats, chips)
        fill_w = int(bar_w * frac)
        if fill_w > 0:
            pygame.draw.rect(surf, challenge.color, (bar_x, bar_y, fill_w, bar_h), border_radius=4)
        pygame.draw.rect(surf, (120, 120, 120), (bar_x, bar_y, bar_w, bar_h), 1, border_radius=4)

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

        label = _action_label(hint)
        color = ACTION_RGB.get(hint, (200, 200, 200))

        # Caja de hint
        padding = 8
        text_s = self._font_hint.render(i18n.t("hud.strategy_hint", label=label), True, color)
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
        text = i18n.t("hud.training_badge", correct=correct, total=total, pct=pct)
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

    # Fase 24: categorías del registro mano-a-mano de la sesión
    # (SessionStats.hand_log), compartidas por la barra de distribución y
    # la leyenda -- el orden importa, es el orden en que se dibuja la barra.
    _RESULT_CATEGORIES = ["blackjack", "win", "push", "loss", "bust", "surrender"]

    @staticmethod
    def _category_color(tag: str) -> tuple:
        return {
            "blackjack": cfg.COLOR_BJ,
            "win":       cfg.COLOR_WIN,
            "push":      cfg.COLOR_PUSH,
            "loss":      cfg.COLOR_LOSE,
            "bust":      (230, 140, 40),
            "surrender": (160, 110, 200),
        }[tag]

    @staticmethod
    def _category_label(tag: str) -> str:
        return i18n.t({
            "blackjack": "hud.category_blackjack",
            "win":       "hud.category_win",
            "push":      "hud.category_push",
            "loss":      "hud.category_loss",
            "bust":      "hud.category_bust",
            "surrender": "hud.category_surrender",
        }[tag])

    def _draw_stats_panel(self, surf: pygame.Surface, engine) -> None:
        s = engine.player.stats
        DIVIDER = None   # marcador: dibuja una línea en vez de texto
        lines = [
            i18n.t("hud.stat_player", name=engine.player.name),
            i18n.t("hud.stat_chips", chips=int(engine.player.chips)),
            DIVIDER,
            i18n.t("hud.stat_hands", n=s.hands_played),
            i18n.t("hud.stat_wlp", w=s.hands_won, l=s.hands_lost, p=s.hands_push),
            i18n.t("hud.stat_winrate", pct=s.win_rate),
            i18n.t("hud.stat_roi", roi=s.roi),
            i18n.t("hud.stat_net", net=s.net_profit),
            DIVIDER,
            i18n.t("hud.stat_blackjacks", n=s.blackjacks),
            i18n.t("hud.stat_busts", n=s.busts),
            i18n.t("hud.stat_best_streak", n=s.best_streak),
        ]
        padding = 10
        divider_h = 9
        chart_w = 300   # ancho de los dos gráficos nuevos (Fase 24)
        line_surfs = [None if l is DIVIDER else self._font_stats.render(l, True, cfg.COLOR_TEXT)
                      for l in lines]
        text_widths = [ls.get_width() for ls in line_surfs if ls is not None]
        text_h = sum((ls.get_height() + 3) if ls is not None else divider_h
                     for ls in line_surfs)

        has_hands = bool(s.hand_log)
        charts_h = 0
        if has_hands:
            # divider + título + barra + leyenda (hasta 3 filas de 2 cols)
            legend_rows = (min(len(self._RESULT_CATEGORIES), len(set(t for t, _ in s.hand_log))) + 1) // 2
            dist_h = divider_h + 16 + 4 + 16 + 4 + legend_rows * 18
            # divider + título + sparkline
            streak_h = divider_h + 16 + 4 + 50
            charts_h = dist_h + streak_h

        box_w = max((max(text_widths) if text_widths else 100) + padding * 2,
                    chart_w + padding * 2)
        box_h = text_h + charts_h + padding * 2
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

        if has_hands:
            icons.hline(surf, x + padding, cy + divider_h // 2, box_w - padding * 2, (90, 90, 90))
            cy += divider_h
            cy = self._draw_result_distribution(surf, x + padding, cy, chart_w, s.hand_log)
            icons.hline(surf, x + padding, cy + divider_h // 2, box_w - padding * 2, (90, 90, 90))
            cy += divider_h
            self._draw_streak_sparkline(surf, x + padding, cy, chart_w, s.hand_log)

    def _draw_result_distribution(self, surf: pygame.Surface, x: int, y: int,
                                   w: int, hand_log: list[tuple[str, int]]) -> int:
        """Barra apilada con la proporción de cada resultado de la sesión
        (Blackjack/Victoria/Empate/Derrota/Pasada/Rendición) + leyenda con
        el recuento de cada uno. Devuelve la y justo debajo de lo dibujado."""
        title = self._font_small.render(i18n.t("hud.result_distribution_title"), True, (170, 170, 170))
        surf.blit(title, (x, y))
        y += title.get_height() + 4

        counts = {tag: 0 for tag in self._RESULT_CATEGORIES}
        for tag, _streak in hand_log:
            if tag in counts:
                counts[tag] += 1
        total = sum(counts.values()) or 1

        bar_h = 16
        bar_rect = pygame.Rect(x, y, w, bar_h)
        pygame.draw.rect(surf, (35, 35, 35), bar_rect, border_radius=5)
        seg_x = x
        for tag in self._RESULT_CATEGORIES:
            n = counts[tag]
            if n <= 0:
                continue
            seg_w = round(w * n / total)
            if seg_w > 0:
                pygame.draw.rect(surf, self._category_color(tag), (seg_x, y, seg_w, bar_h))
            seg_x += seg_w
        pygame.draw.rect(surf, cfg.COLOR_GOLD, bar_rect, 1, border_radius=5)
        y += bar_h + 4

        present = [t for t in self._RESULT_CATEGORIES if counts[t] > 0]
        col_w = w // 2
        for i, tag in enumerate(present):
            col, row = i % 2, i // 2
            lx = x + col * col_w
            ly = y + row * 18
            pygame.draw.rect(surf, self._category_color(tag), (lx, ly + 3, 10, 10), border_radius=2)
            label = i18n.t("hud.category_count_label", label=self._category_label(tag), n=counts[tag])
            ls = self._font_small.render(label, True, (190, 190, 190))
            surf.blit(ls, (lx + 16, ly))
        rows = (len(present) + 1) // 2
        return y + rows * 18

    def _draw_streak_sparkline(self, surf: pygame.Surface, x: int, y: int,
                                w: int, hand_log: list[tuple[str, int]]) -> int:
        """Barras verticales con la racha (+ ganando / - perdiendo) tras
        cada mano de la sesión, las últimas ~30 -- de un vistazo se ve si
        la sesión va a rachas o muy plana. Devuelve la y justo debajo."""
        chart_h = 50
        max_bars = 30
        recent = hand_log[-max_bars:]
        current = hand_log[-1][1] if hand_log else 0

        title = self._font_small.render(
            i18n.t("hud.streak_sparkline_title", current=current), True, (170, 170, 170))
        surf.blit(title, (x, y))
        y += title.get_height() + 4

        baseline = y + chart_h // 2
        icons.hline(surf, x, baseline, w, (70, 70, 70))

        n = len(recent)
        if n > 0:
            scale = 8   # racha considerada "a tope de barra" (clamp visual)
            half_h = (chart_h // 2) - 2
            bar_w = max(3, w // n - 2)
            gap = (w - bar_w * n) / n if n else 0
            bx = x
            for _tag, streak in recent:
                clamped = max(-scale, min(scale, streak))
                seg_h = int(abs(clamped) / scale * half_h)
                color = cfg.COLOR_WIN if streak > 0 else (cfg.COLOR_LOSE if streak < 0 else (120, 120, 120))
                if seg_h <= 0:
                    pygame.draw.rect(surf, color, (int(bx), baseline - 1, bar_w, 2))
                elif streak > 0:
                    pygame.draw.rect(surf, color, (int(bx), baseline - seg_h, bar_w, seg_h))
                else:
                    pygame.draw.rect(surf, color, (int(bx), baseline, bar_w, seg_h))
                bx += bar_w + gap
        return y + chart_h

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
        title = title_font.render(
            i18n.t("hud.achievements_title", n=n_unlocked, total=len(ACHIEVEMENTS)), True, cfg.COLOR_GOLD)
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
            ach_name, ach_desc = i18n.achievement_text(ach)
            name_s = self._font_stats.render(ach_name, True, name_col)
            desc_s = self._font_small.render(ach_desc, True, desc_col)
            tx = cx0 + icon_r * 2 + 10
            surf.blit(name_s, (tx, cy0 + 2))
            surf.blit(desc_s, (tx, cy0 + 2 + name_s.get_height()))