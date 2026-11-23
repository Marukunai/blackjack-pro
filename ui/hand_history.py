# ui/hand_history.py
# Pantalla de historial de manos: navega el registro completo guardado en
# la tabla hand_history (SQLite, ver engine/profile_store.py) desde la
# Fase 5 -- nunca se sobrescribe, así que esta pantalla es la única forma
# de verlo más allá de la última ronda jugada.
#
# Acepta una lista de perfiles (no solo uno): si hay más de uno se
# dibujan pestañas arriba para saltar de perfil sin salir de la pantalla
# -- así sirve tanto para "ver el historial de ESTE perfil" (desde
# ProfileSelect, con la lista completa de perfiles locales) como para
# "ver el historial de quien está jugando ahora" (desde MainMenu, con
# los 1-3 perfiles sentados a la mesa en esta sesión).
# -------------------------------------------------------------
from __future__ import annotations

import time
import pygame
from typing import Optional

from config import settings as cfg
from config import i18n
from engine.profile_store import get_store
from ui import icons

PAGE_SIZE = 12
CHART_LIMIT = 300   # nº máximo de manos que entran en la gráfica de evolución

# Anchos de columna de la tabla, reutilizados también para alinear el
# ancho de la gráfica de evolución con la tabla que tiene debajo. El
# segundo elemento de cada tupla es ahora la clave i18n de la etiqueta
# (se traduce en vivo en _draw_table), no el texto en sí.
_TABLE_COLS = [
    ("history.col_date", 190), ("history.col_casino", 190), ("history.col_bet", 100),
    ("history.col_result", 160), ("history.col_net", 110), ("history.col_chips", 110),
]
_TABLE_W = sum(w for _, w in _TABLE_COLS)

# Mismos colores que usa ui/renderer.py para RoundResult en la pantalla de
# resultado, indexados por el nombre de enum (str) tal como se guarda en
# hand_history.result -- así el historial se ve igual que el mensaje que
# ya vio el jugador al terminar esa mano. El TEXTO (antes vivía en un
# _RESULT_LABELS de por aquí) ahora sale de i18n.hand_result_label(), que
# tanto este módulo como ui/hand_replay.py usan por igual -- evita que
# vuelva a pasar el bug de la Fase 26 (ver ui/hand_replay.py) en que un
# consumidor de un diccionario de "etiquetas" se quedó sin envolver el
# valor en i18n.t() al convertirse ese diccionario de texto a claves.
_RESULT_COLORS = {
    "WIN":            cfg.COLOR_WIN,
    "BLACKJACK_WIN":  cfg.COLOR_BJ,
    "DEALER_BUST":    cfg.COLOR_WIN,
    "LOSS":           cfg.COLOR_LOSE,
    "PUSH":           cfg.COLOR_PUSH,
    "SURRENDER":      cfg.COLOR_PUSH,
}


class HandHistoryScreen:
    """
    Pantalla de solo lectura: historial paginado de manos jugadas por uno
    o más perfiles locales. Bucle bloqueante; Volver/Esc cierra sin
    devolver nada (no cambia ningún dato).
    """

    def __init__(self, screen: pygame.Surface, profiles: list[tuple[int, str]],
                 initial_index: int = 0) -> None:
        self.screen = screen
        self.sw, self.sh = screen.get_size()
        self.store = get_store()
        self.profiles = profiles or [(None, i18n.t("history.default_player_name"))]
        self._idx = max(0, min(len(self.profiles) - 1, initial_index))

        self._font_title = pygame.font.SysFont(None, 38, bold=True)
        self._font_tab   = pygame.font.SysFont(None, 20, bold=True)
        self._font_head  = pygame.font.SysFont(None, 18, bold=True)
        self._font_row   = pygame.font.SysFont(None, 18)
        self._font_small = pygame.font.SysFont(None, 16)

        self._done = False
        self._page = 0
        self._rows: list[dict] = []
        self._total = 0
        self._chip_curve: list[float] = []
        self._load_profile()

        self._back_rect = pygame.Rect(self.sw // 2 - 90, self.sh - 78, 180, 44)
        # Fase 29: botón de exportar CSV, a la izquierda de Volver con
        # separación fija -- mismo eje Y y alto, así que nunca se solapan
        # sea cual sea el idioma (el texto del botón se centra dentro de
        # un ancho fijo, no crece con la traducción).
        self._export_rect = pygame.Rect(self._back_rect.x - 20 - 170, self.sh - 78, 170, 44)
        # Fase 42: botón para alternar entre la tabla de siempre y la
        # vista "avanzada" (varianza/drawdown, desglose de apuestas
        # laterales, resultados de Torneo) -- a la derecha de Volver,
        # simétrico con Exportar CSV a su izquierda, mismo alto y eje Y
        # que ya usan esos dos botones así que nunca se solapan.
        self._advanced_rect = pygame.Rect(self._back_rect.right + 20, self.sh - 78, 170, 44)
        self._prev_rect = pygame.Rect(0, 0, 0, 0)
        self._next_rect = pygame.Rect(0, 0, 0, 0)
        self._tab_rects: list[pygame.Rect] = []
        self._replay_rects: list[tuple[pygame.Rect, dict]] = []
        self._back_hover = self._prev_hover = self._next_hover = self._export_hover = False
        self._advanced_hover = False
        self._export_msg: Optional[str] = None
        self._export_msg_color: tuple = (150, 150, 150)
        self._export_msg_until: float = 0.0

        # Fase 42: "table" (de siempre) o "advanced" -- datos cargados en
        # _load_advanced(), llamada desde _load_profile() cada vez que se
        # cambia de perfil, igual que _chip_curve.
        self._view_mode: str = "table"
        self._risk_metrics: dict = {}
        self._side_bet_breakdown: dict = {}
        self._tournament_results: list = []
        self._load_advanced()

    # ------------------------------------------------------------------
    @property
    def profile_id(self):
        return self.profiles[self._idx][0]

    @property
    def profile_name(self) -> str:
        return self.profiles[self._idx][1]

    @property
    def _page_count(self) -> int:
        return max(1, (self._total + PAGE_SIZE - 1) // PAGE_SIZE)

    def _load_profile(self) -> None:
        self._page = 0
        pid = self.profile_id
        self._total = self.store.count_history(pid) if pid is not None else 0
        self._chip_curve = self.store.get_chip_curve(pid, limit=CHART_LIMIT) if pid is not None else []
        self._load_advanced()
        self._load_page()

    def _load_advanced(self) -> None:
        """Datos de la vista "avanzada" (Fase 42): métricas de riesgo,
        desglose de apuestas laterales y resultados de Torneo -- del
        perfil actualmente seleccionado en las pestañas, no de todos."""
        pid = self.profile_id
        if pid is None:
            self._risk_metrics = {}
            self._side_bet_breakdown = {}
            self._tournament_results = []
            return
        from engine.statistics import compute_risk_metrics
        self._risk_metrics = compute_risk_metrics(pid)
        self._side_bet_breakdown = self.store.get_side_bet_breakdown(pid)
        self._tournament_results = self.store.get_tournament_results(pid, limit=10)

    def _load_page(self) -> None:
        pid = self.profile_id
        if pid is None:
            self._rows = []
            return
        self._rows = self.store.get_history(
            pid, limit=PAGE_SIZE, offset=self._page * PAGE_SIZE)

    def _switch_profile(self, delta: int) -> None:
        if len(self.profiles) <= 1:
            return
        self._idx = (self._idx + delta) % len(self.profiles)
        self._load_profile()

    def _go_page(self, delta: int) -> None:
        new_page = max(0, min(self._page_count - 1, self._page + delta))
        if new_page != self._page:
            self._page = new_page
            self._load_page()

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

    def _handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self._done = True
            elif event.key in (pygame.K_LEFT, pygame.K_PAGEUP):
                self._go_page(-1)
            elif event.key in (pygame.K_RIGHT, pygame.K_PAGEDOWN):
                self._go_page(1)
            elif event.key == pygame.K_TAB:
                mods = pygame.key.get_mods()
                self._switch_profile(-1 if mods & pygame.KMOD_SHIFT else 1)
            elif event.key == pygame.K_e:
                self._export_csv()

        if event.type == pygame.MOUSEMOTION:
            self._back_hover = self._back_rect.collidepoint(event.pos)
            self._export_hover = self._export_rect.collidepoint(event.pos)
            self._advanced_hover = self._advanced_rect.collidepoint(event.pos)
            self._prev_hover = self._prev_rect.collidepoint(event.pos)
            self._next_hover = self._next_rect.collidepoint(event.pos)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._back_rect.collidepoint(event.pos):
                self._done = True
                return
            if self._total > 0 and self._export_rect.collidepoint(event.pos):
                self._export_csv()
                return
            if self.profile_id is not None and self._advanced_rect.collidepoint(event.pos):
                self._view_mode = "advanced" if self._view_mode == "table" else "table"
                return
            if self._prev_rect.collidepoint(event.pos):
                self._go_page(-1)
                return
            if self._next_rect.collidepoint(event.pos):
                self._go_page(1)
                return
            for i, r in enumerate(self._tab_rects):
                if r.collidepoint(event.pos):
                    if i != self._idx:
                        self._idx = i
                        self._load_profile()
                    return
            for r, row in self._replay_rects:
                if r.collidepoint(event.pos):
                    self._open_replay(row)
                    return

    def _export_csv(self) -> None:
        """Fase 29: exporta el historial completo (todas las manos, no
        solo la página actual) + el resumen de estadísticas del perfil
        activo a un CSV en saves/exports/. Sin perfil con manos
        registradas no hay nada que hacer -- el botón ni se dibuja en
        ese caso (ver _draw_back), pero la tecla E podría pulsarse igual."""
        if self.profile_id is None or self._total == 0:
            return
        # Import diferido, mismo motivo que _open_replay: solo se paga el
        # coste de importar csv/engine.csv_export si de verdad se exporta.
        from engine.csv_export import export_profile_csv, ExportError
        try:
            path = export_profile_csv(self.profile_id)
        except (ExportError, OSError) as e:
            self._export_msg = i18n.t("history.export_error")
            self._export_msg_color = cfg.COLOR_LOSE
        else:
            self._export_msg = i18n.t("history.export_success", filename=path.name)
            self._export_msg_color = cfg.COLOR_WIN
        self._export_msg_until = time.time() + 5.0

    def _open_replay(self, row: dict) -> None:
        # Import diferido: evita un ciclo de importación (hand_replay
        # importa las etiquetas de resultado de este mismo módulo) y solo
        # se paga el coste si de verdad se abre una repetición.
        from ui.hand_replay import HandReplayScreen
        HandReplayScreen(self.screen, row).run()

    # ------------------------------------------------------------------
    # Dibujo
    # ------------------------------------------------------------------
    def _draw(self) -> None:
        surf = self.screen
        surf.fill(cfg.COLOR_BG)

        top = 30
        if len(self.profiles) > 1:
            self._draw_tabs(surf, top)
            top += 44

        title = self._font_title.render(
            i18n.t("history.title_for_profile", name=self.profile_name), True, cfg.COLOR_GOLD)
        surf.blit(title, (self.sw // 2 - title.get_width() // 2, top))
        top += 56

        if self._view_mode == "advanced" and self.profile_id is not None:
            self._draw_advanced(surf, top)
        elif self._total == 0:
            empty = self._font_row.render(
                i18n.t("history.empty_state"), True, (150, 150, 150))
            surf.blit(empty, (self.sw // 2 - empty.get_width() // 2, top + 60))
        else:
            self._draw_table(surf, top)
            self._draw_chip_chart(surf)

        if self._view_mode == "table":
            self._draw_pagination(surf)
        self._draw_back(surf)

    def _draw_tabs(self, surf: pygame.Surface, y: int) -> None:
        gap = 10
        rects = []
        widths = [self._font_tab.size(name)[0] + 28 for _, name in self.profiles]
        total_w = sum(widths) + gap * (len(widths) - 1)
        x = self.sw // 2 - total_w // 2
        for i, ((_, name), w) in enumerate(zip(self.profiles, widths)):
            r = pygame.Rect(x, y, w, 32)
            rects.append(r)
            active = (i == self._idx)
            bg = (212, 175, 55, 35) if active else (255, 255, 255, 10)
            box = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
            pygame.draw.rect(box, bg, box.get_rect(), border_radius=16)
            pygame.draw.rect(box, cfg.COLOR_GOLD if active else (100, 100, 100),
                              box.get_rect(), 1, border_radius=16)
            surf.blit(box, (r.x, r.y))
            col = cfg.COLOR_GOLD if active else (180, 180, 180)
            t = self._font_tab.render(name, True, col)
            surf.blit(t, (r.centerx - t.get_width() // 2, r.centery - t.get_height() // 2))
            x += w + gap
        self._tab_rects = rects

    def _draw_table(self, surf: pygame.Surface, top: int) -> None:
        cols = _TABLE_COLS
        table_w = _TABLE_W
        x0 = self.sw // 2 - table_w // 2
        y = top
        self._replay_rects = []

        cx = x0
        for label_key, w in cols:
            lbl = self._font_head.render(i18n.t(label_key), True, (150, 150, 150))
            surf.blit(lbl, (cx, y))
            cx += w
        y += 26
        pygame.draw.line(surf, (80, 80, 80), (x0, y), (x0 + table_w, y), 1)
        y += 10

        row_h = 30
        for i, row in enumerate(self._rows):
            if i % 2 == 1:
                band = pygame.Surface((table_w, row_h), pygame.SRCALPHA)
                band.fill((255, 255, 255, 8))
                surf.blit(band, (x0, y - 4))

            cx = x0
            try:
                date_str = time.strftime("%d/%m/%Y %H:%M", time.localtime(row["played_at"]))
            except (OSError, ValueError):
                date_str = "—"
            surf.blit(self._font_row.render(date_str, True, cfg.COLOR_TEXT), (cx, y))
            cx += cols[0][1]

            preset_name = row.get("preset_name")
            preset = i18n.preset_label(preset_name) if preset_name else "—"
            surf.blit(self._font_row.render(preset, True, cfg.COLOR_TEXT), (cx, y))
            cx += cols[1][1]

            surf.blit(self._font_row.render(f"${row['bet']:.0f}", True, cfg.COLOR_TEXT), (cx, y))
            cx += cols[2][1]

            result_key = row["result"]
            label = i18n.hand_result_label(result_key)
            color = _RESULT_COLORS.get(result_key, cfg.COLOR_TEXT)
            surf.blit(self._font_row.render(label, True, color), (cx, y))
            cx += cols[3][1]

            net = row["net"]
            net_col = cfg.COLOR_WIN if net > 0 else (cfg.COLOR_LOSE if net < 0 else cfg.COLOR_PUSH)
            surf.blit(self._font_row.render(f"{net:+.0f}", True, net_col), (cx, y))
            cx += cols[4][1]

            surf.blit(self._font_row.render(f"{row['chips_after']:.0f}", True, (200, 200, 200)), (cx, y))
            cx += cols[5][1]

            if row.get("replay_data"):
                btn_r = pygame.Rect(cx + 14, y - 4, 26, 26)
                hover = btn_r.collidepoint(pygame.mouse.get_pos())
                col = cfg.COLOR_GOLD if hover else (140, 140, 140)
                icons.triangle_right(surf, btn_r.centerx - 3, btn_r.centery, 8, col)
                self._replay_rects.append((btn_r, row))

            y += row_h

    def _draw_chip_chart(self, surf: pygame.Surface) -> None:
        """Gráfica simple de evolución de fichas a lo largo de las últimas
        manos (hasta CHART_LIMIT), en un panel fijo entre la tabla y la
        paginación -- no se solapa con ninguna de las dos porque su
        posición no depende de cuántas filas tenga la página actual."""
        curve = self._chip_curve
        if len(curve) < 2:
            return

        x0 = self.sw // 2 - _TABLE_W // 2
        chart_bottom = self.sh - 142
        chart_top = self.sh - 252
        rect = pygame.Rect(x0, chart_top, _TABLE_W, chart_bottom - chart_top)

        box = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        pygame.draw.rect(box, (255, 255, 255, 8), box.get_rect(), border_radius=8)
        pygame.draw.rect(box, (80, 80, 80), box.get_rect(), 1, border_radius=8)
        surf.blit(box, (rect.x, rect.y))

        label = self._font_head.render(
            i18n.t("history.chip_evolution_label", n=len(curve)), True, (170, 170, 170))
        surf.blit(label, (rect.x + 14, rect.y + 8))

        plot = pygame.Rect(rect.x + 14, rect.y + 30, rect.w - 28, rect.h - 44)

        lo, hi = min(curve), max(curve)
        if hi - lo < 1e-6:
            hi = lo + 1.0

        n = len(curve)
        points = [
            (plot.x + (i / (n - 1)) * plot.w,
             plot.bottom - ((v - lo) / (hi - lo)) * plot.h)
            for i, v in enumerate(curve)
        ]

        trend_col = cfg.COLOR_WIN if curve[-1] >= curve[0] else cfg.COLOR_LOSE

        # Área rellena bajo la línea, semitransparente.
        fill = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        offset = (rect.x, rect.y)
        fill_pts = [(px - offset[0], py - offset[1]) for px, py in points]
        fill_pts += [(plot.right - offset[0], plot.bottom - offset[1]),
                     (plot.x - offset[0], plot.bottom - offset[1])]
        pygame.draw.polygon(fill, (*trend_col[:3], 30), fill_pts)
        surf.blit(fill, (rect.x, rect.y))

        if n > 1:
            pygame.draw.lines(surf, trend_col, False, points, 2)
        pygame.draw.circle(surf, trend_col, (int(points[-1][0]), int(points[-1][1])), 4)

        # Etiquetas de escala (máximo arriba, mínimo abajo) -- a la
        # izquierda del todo, para que nunca puedan solaparse con la
        # etiqueta del valor actual (junto al último punto, extremo
        # derecho). Se dibujan DESPUÉS de la línea/relleno, con un
        # pequeño fondo opaco propio, para que sigan siendo legibles
        # aunque la curva pase justo por encima (p. ej. cuando el máximo
        # o el mínimo de la ventana son también de los primeros puntos).
        self._blit_label_with_backing(surf, f"{hi:.0f}", (plot.x, plot.y - 2), (130, 130, 130))
        self._blit_label_with_backing(
            surf, f"{lo:.0f}", (plot.x, plot.bottom - self._font_small.get_height() + 2), (130, 130, 130))

        cur_lbl = self._font_small.render(f"{curve[-1]:.0f}", True, trend_col)
        cur_x = min(points[-1][0] + 8, rect.right - cur_lbl.get_width() - 6)
        above_y = points[-1][1] - cur_lbl.get_height() - 4
        # Si el último punto está cerca del techo de la gráfica no cabe
        # una etiqueta encima (pisaría el título del panel) -- se dibuja
        # debajo del punto en su lugar.
        cur_y = above_y if above_y >= plot.y - 2 else points[-1][1] + 6
        self._blit_label_with_backing(surf, f"{curve[-1]:.0f}", (cur_x, cur_y), trend_col)

    def _blit_label_with_backing(self, surf: pygame.Surface, text: str,
                                  pos: tuple, color: tuple) -> None:
        """Dibuja una etiqueta de texto pequeña con un fondo opaco propio
        detrás, para que quede legible aunque se superponga con la línea
        o el área rellena de la gráfica."""
        lbl = self._font_small.render(text, True, color)
        bg_rect = lbl.get_rect(topleft=pos).inflate(4, 2)
        pygame.draw.rect(surf, cfg.COLOR_BG, bg_rect, border_radius=3)
        surf.blit(lbl, pos)

    def _draw_advanced(self, surf: pygame.Surface, top: int) -> None:
        """Vista "avanzada" (Fase 42): varianza/drawdown, desglose de
        rentabilidad por apuesta lateral y resultados de Torneo del
        perfil activo -- sustituye a la tabla+gráfica de siempre en el
        mismo hueco, así que no necesita su propio scroll ni paginación."""
        x0 = self.sw // 2 - _TABLE_W // 2
        y = top

        m = self._risk_metrics
        if not m or m.get("hands", 0) < 2:
            msg = self._font_row.render(i18n.t("history.advanced_no_data"), True, (150, 150, 150))
            surf.blit(msg, (x0, y))
            y += 40
        else:
            risk_title = self._font_head.render(i18n.t("history.advanced_risk_title"), True, cfg.COLOR_GOLD)
            surf.blit(risk_title, (x0, y))
            y += 26
            lines = [
                i18n.t("history.advanced_hands_analyzed", n=m["hands"]),
                i18n.t("history.advanced_stddev", value=f"{m['net_stddev']:.1f}"),
                i18n.t("history.advanced_drawdown", value=f"{m['max_drawdown']:.0f}",
                       pct=f"{m['max_drawdown_pct']:.1%}"),
            ]
            for line in lines:
                lbl = self._font_row.render(line, True, cfg.COLOR_TEXT)
                surf.blit(lbl, (x0, y))
                y += 24
            y += 10

        y = self._draw_side_bet_breakdown(surf, x0, y)
        self._draw_tournament_results(surf, x0, y)

    def _draw_side_bet_breakdown(self, surf: pygame.Surface, x0: int, y: int) -> int:
        title = self._font_head.render(i18n.t("history.advanced_sidebets_title"), True, cfg.COLOR_GOLD)
        surf.blit(title, (x0, y))
        y += 28

        breakdown = self._side_bet_breakdown
        if not breakdown:
            empty = self._font_small.render(i18n.t("history.advanced_sidebets_empty"), True, (130, 130, 130))
            surf.blit(empty, (x0, y))
            return y + 34

        cols = [
            (i18n.t("history.advanced_sidebets_col_type"), 180),
            (i18n.t("history.advanced_sidebets_col_count"), 110),
            (i18n.t("history.advanced_sidebets_col_wagered"), 130),
            (i18n.t("history.advanced_sidebets_col_net"), 130),
            (i18n.t("history.advanced_sidebets_col_hitrate"), 120),
        ]
        cx = x0
        for label, w in cols:
            lbl = self._font_head.render(label, True, (150, 150, 150))
            surf.blit(lbl, (cx, y))
            cx += w
        y += 24

        for kind, data in sorted(breakdown.items(), key=lambda kv: kv[1]["wagered"], reverse=True):
            cx = x0
            surf.blit(self._font_row.render(i18n.side_bet_kind_label(kind), True, cfg.COLOR_TEXT), (cx, y))
            cx += cols[0][1]
            surf.blit(self._font_row.render(str(data["count"]), True, cfg.COLOR_TEXT), (cx, y))
            cx += cols[1][1]
            surf.blit(self._font_row.render(f"${data['wagered']:.0f}", True, cfg.COLOR_TEXT), (cx, y))
            cx += cols[2][1]
            net = data["net"]
            net_col = cfg.COLOR_WIN if net > 0 else (cfg.COLOR_LOSE if net < 0 else cfg.COLOR_PUSH)
            surf.blit(self._font_row.render(f"{net:+.0f}", True, net_col), (cx, y))
            cx += cols[3][1]
            hit_pct = (data["hits"] / data["count"] * 100.0) if data["count"] else 0.0
            surf.blit(self._font_row.render(f"{hit_pct:.0f}%", True, cfg.COLOR_TEXT), (cx, y))
            y += 24

        return y + 14

    def _draw_tournament_results(self, surf: pygame.Surface, x0: int, y: int) -> int:
        title = self._font_head.render(i18n.t("history.advanced_tournaments_title"), True, cfg.COLOR_GOLD)
        surf.blit(title, (x0, y))
        y += 28

        results = self._tournament_results
        if not results:
            empty = self._font_small.render(i18n.t("history.advanced_tournaments_empty"), True, (130, 130, 130))
            surf.blit(empty, (x0, y))
            return y + 34

        cols = [
            (i18n.t("history.advanced_tournaments_col_date"), 190),
            (i18n.t("history.advanced_tournaments_col_name"), 220),
            (i18n.t("history.advanced_tournaments_col_rank"), 130),
            (i18n.t("history.advanced_tournaments_col_chips"), 160),
        ]
        cx = x0
        for label, w in cols:
            lbl = self._font_head.render(label, True, (150, 150, 150))
            surf.blit(lbl, (cx, y))
            cx += w
        y += 24

        for row in results:
            cx = x0
            try:
                date_str = time.strftime("%d/%m/%Y %H:%M", time.localtime(row["played_at"]))
            except (OSError, ValueError):
                date_str = "—"
            surf.blit(self._font_row.render(date_str, True, cfg.COLOR_TEXT), (cx, y))
            cx += cols[0][1]
            surf.blit(self._font_row.render(row["tournament_name"], True, cfg.COLOR_TEXT), (cx, y))
            cx += cols[1][1]
            rank_col = {1: cfg.COLOR_BJ, 2: (205, 205, 205), 3: (205, 140, 80)}.get(row["rank"], cfg.COLOR_TEXT)
            surf.blit(self._font_row.render(f"{row['rank']}/{row['seats']}", True, rank_col), (cx, y))
            cx += cols[2][1]
            surf.blit(self._font_row.render(f"${row['final_chips']:.0f}", True, cfg.COLOR_TEXT), (cx, y))
            y += 24

        return y + 14

    def _draw_pagination(self, surf: pygame.Surface) -> None:
        pag_y = self.sh - 128
        self._prev_rect = pygame.Rect(self.sw // 2 - 170, pag_y, 40, 36)
        self._next_rect = pygame.Rect(self.sw // 2 + 130, pag_y, 40, 36)
        can_prev = self._page > 0
        can_next = self._page < self._page_count - 1

        prev_col = (cfg.COLOR_GOLD if self._prev_hover else (170, 170, 170)) if can_prev else (60, 60, 60)
        next_col = (cfg.COLOR_GOLD if self._next_hover else (170, 170, 170)) if can_next else (60, 60, 60)
        icons.triangle_left(surf, self._prev_rect.centerx + 6, self._prev_rect.centery, 14, prev_col)
        icons.triangle_right(surf, self._next_rect.centerx - 6, self._next_rect.centery, 14, next_col)

        page_lbl = self._font_row.render(
            i18n.t("history.pagination_label", page=self._page + 1,
                   total_pages=self._page_count, total=self._total),
            True, (180, 180, 180))
        surf.blit(page_lbl, (self.sw // 2 - page_lbl.get_width() // 2, pag_y + 8))

    def _draw_back(self, surf: pygame.Surface) -> None:
        back_col = cfg.COLOR_GOLD if self._back_hover else (150, 150, 150)
        pygame.draw.rect(surf, (20, 15, 0), self._back_rect, border_radius=10)
        pygame.draw.rect(surf, back_col, self._back_rect, 2, border_radius=10)
        back_txt = self._font_row.render(i18n.t("history.back_button"), True, back_col)
        surf.blit(back_txt, (self._back_rect.centerx - back_txt.get_width() // 2,
                              self._back_rect.centery - back_txt.get_height() // 2))

        # Fase 29: el botón de exportar solo aparece si hay algo que
        # exportar -- igual que el propio bloque de tabla/gráfica de
        # arriba, que tampoco se dibuja con self._total == 0.
        if self._total > 0:
            exp_col = cfg.COLOR_GOLD if self._export_hover else (150, 150, 150)
            pygame.draw.rect(surf, (20, 15, 0), self._export_rect, border_radius=10)
            pygame.draw.rect(surf, exp_col, self._export_rect, 2, border_radius=10)
            exp_txt = self._font_row.render(i18n.t("history.export_button"), True, exp_col)
            surf.blit(exp_txt, (self._export_rect.centerx - exp_txt.get_width() // 2,
                                 self._export_rect.centery - exp_txt.get_height() // 2))

        # Fase 42: alterna entre la tabla de siempre y la vista avanzada
        # -- solo tiene sentido con un perfil con fichas/historial propio.
        if self.profile_id is not None:
            adv_col = cfg.COLOR_GOLD if self._advanced_hover else (150, 150, 150)
            pygame.draw.rect(surf, (20, 15, 0), self._advanced_rect, border_radius=10)
            pygame.draw.rect(surf, adv_col, self._advanced_rect, 2, border_radius=10)
            adv_key = "history.table_view_button" if self._view_mode == "advanced" else "history.advanced_button"
            adv_txt = self._font_row.render(i18n.t(adv_key), True, adv_col)
            surf.blit(adv_txt, (self._advanced_rect.centerx - adv_txt.get_width() // 2,
                                 self._advanced_rect.centery - adv_txt.get_height() // 2))

        # La línea inferior de pistas de teclado se sustituye unos
        # segundos por el resultado de la exportación (éxito/error) en
        # vez de añadir una zona nueva a la pantalla -- mismo sitio,
        # mismo tamaño de fuente, así que no hay riesgo de solape nuevo.
        if self._export_msg and time.time() < self._export_msg_until:
            msg = self._font_small.render(self._export_msg, True, self._export_msg_color)
            surf.blit(msg, (self.sw // 2 - msg.get_width() // 2, self.sh - 24))
            return

        # Fase 42: en vista avanzada no hay paginación que recorrer con
        # flechas, así que esa pista se omite (y no pisa sitio si la
        # pista de exportar sigue presente, que sí tiene sentido en
        # ambas vistas: el CSV siempre exporta el historial completo).
        hint_parts = ([i18n.t("history.hint_page_arrows")] if self._view_mode == "table" else []) \
            + [i18n.t("history.hint_esc_exit")]
        if len(self.profiles) > 1:
            hint_parts.insert(len(hint_parts) - 1, i18n.t("history.hint_tab_switch"))
        if self._total > 0:
            hint_parts.insert(-1, i18n.t("history.export_hint"))
        hint = self._font_small.render(" · ".join(hint_parts), True, (90, 90, 90))
        surf.blit(hint, (self.sw // 2 - hint.get_width() // 2, self.sh - 24))
