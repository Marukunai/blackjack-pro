# ui/leaderboard.py
# Pantalla de comparativa de perfiles ("leaderboard"): compara todos los
# perfiles locales entre sí -- fichas, manos jugadas, % de victorias,
# blackjacks, mejor racha y logros -- en una tabla ordenable por columna
# (click en la cabecera). Pantalla de solo lectura, mismo patrón que
# HandHistoryScreen: bucle bloqueante, Volver/Esc cierra sin devolver
# nada, no toca ningún dato.
# -------------------------------------------------------------
from __future__ import annotations

import pygame

from config import settings as cfg
from engine.profile_store import get_store
from engine.achievements import ACHIEVEMENTS
from ui.profile_select import draw_avatar

_TOTAL_ACHIEVEMENTS = len(ACHIEVEMENTS)

# (key, etiqueta, ancho en px). "rank" no es clickable -- es la posición
# resultante de ordenar por la columna activa, no una columna en sí.
_COLUMNS: list[tuple[str, str, int]] = [
    ("rank",         "#",           40),
    ("name",         "Perfil",      200),
    ("chips",        "Fichas",      120),
    ("hands_played", "Manos",       100),
    ("win_pct",      "% Victorias", 130),
    ("blackjacks",   "Blackjacks",  120),
    ("best_streak",  "Mejor racha", 120),
    ("achievements", "Logros",      110),
]


def _row_data(store, p: dict) -> dict:
    hands = p.get("hands_played", 0) or 0
    won = p.get("hands_won", 0) or 0
    win_pct = (won / hands * 100.0) if hands else 0.0
    n_ach = len(store.get_unlocked_achievement_ids(p["id"]))
    return {
        "id": p["id"], "name": p["name"],
        "avatar_shape": p.get("avatar_shape", "S"),
        "avatar_color": p.get("avatar_color", "212,175,55"),
        "chips": p.get("chips", 0.0),
        "hands_played": hands,
        "win_pct": win_pct,
        "blackjacks": p.get("blackjacks", 0),
        "best_streak": p.get("best_streak", 0),
        "achievements": n_ach,
    }


class LeaderboardScreen:
    """
    Compara todos los perfiles locales en una tabla ordenable: click en
    una cabecera de columna ordena por ella (descendente primero, salvo
    el nombre que empieza alfabético); click de nuevo en la misma
    invierte el orden. Bucle bloqueante; Volver/Esc cierra sin devolver
    nada.
    """

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.sw, self.sh = screen.get_size()
        self.store = get_store()

        self._font_title = pygame.font.SysFont(None, 38, bold=True)
        self._font_head  = pygame.font.SysFont(None, 19, bold=True)
        self._font_row   = pygame.font.SysFont(None, 19)
        self._font_small = pygame.font.SysFont(None, 16)

        self._done = False
        self._sort_key = "chips"
        self._sort_desc = True

        self._rows: list[dict] = []
        self._col_rects: list[tuple[str, pygame.Rect]] = []
        self._back_rect = pygame.Rect(self.sw // 2 - 90, self.sh - 78, 180, 44)
        self._back_hover = False

        self._reload()

    # ------------------------------------------------------------------
    def _reload(self) -> None:
        profiles = self.store.list_profiles()
        self._rows = [_row_data(self.store, p) for p in profiles]
        self._sort()

    def _sort(self) -> None:
        key = self._sort_key
        if key == "name":
            self._rows.sort(key=lambda r: r["name"].lower(), reverse=self._sort_desc)
        else:
            self._rows.sort(key=lambda r: r[key], reverse=self._sort_desc)

    def _set_sort(self, key: str) -> None:
        if key == self._sort_key:
            self._sort_desc = not self._sort_desc
        else:
            self._sort_key = key
            self._sort_desc = (key != "name")
        self._sort()

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

        if event.type == pygame.MOUSEMOTION:
            self._back_hover = self._back_rect.collidepoint(event.pos)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._back_rect.collidepoint(event.pos):
                self._done = True
                return
            for key, rect in self._col_rects:
                if rect.collidepoint(event.pos):
                    self._set_sort(key)
                    return

    # ------------------------------------------------------------------
    # Dibujo
    # ------------------------------------------------------------------
    def _draw(self) -> None:
        surf = self.screen
        surf.fill(cfg.COLOR_BG)

        title = self._font_title.render("Comparativa de perfiles", True, cfg.COLOR_GOLD)
        surf.blit(title, (self.sw // 2 - title.get_width() // 2, 40))
        sub = self._font_small.render(
            "Click en una columna para ordenar por ella", True, (140, 140, 140))
        surf.blit(sub, (self.sw // 2 - sub.get_width() // 2, 84))

        top = 130
        if not self._rows:
            empty = self._font_row.render(
                "Todavía no hay perfiles para comparar.", True, (150, 150, 150))
            surf.blit(empty, (self.sw // 2 - empty.get_width() // 2, top + 60))
        else:
            self._draw_table(surf, top)

        self._draw_back(surf)

    def _draw_table(self, surf: pygame.Surface, top: int) -> None:
        table_w = sum(w for _, _, w in _COLUMNS)
        x0 = self.sw // 2 - table_w // 2
        y = top

        self._col_rects = []
        cx = x0
        for key, label, w in _COLUMNS:
            active = (key == self._sort_key)
            col = cfg.COLOR_GOLD if active else (150, 150, 150)
            lbl = self._font_head.render(label, True, col)
            surf.blit(lbl, (cx, y))
            if active:
                self._draw_sort_arrow(surf, cx + lbl.get_width() + 10, y + 9, self._sort_desc, col)
            if key != "rank":
                self._col_rects.append((key, pygame.Rect(cx, y, w, 24)))
            cx += w
        y += 26
        pygame.draw.line(surf, (80, 80, 80), (x0, y), (x0 + table_w, y), 1)
        y += 10

        row_h = 34
        for i, row in enumerate(self._rows):
            if i % 2 == 1:
                band = pygame.Surface((table_w, row_h), pygame.SRCALPHA)
                band.fill((255, 255, 255, 8))
                surf.blit(band, (x0, y - 4))

            cx = x0
            rank = i + 1
            rank_col = {1: cfg.COLOR_BJ, 2: (205, 205, 205), 3: (205, 140, 80)}.get(rank, (140, 140, 140))
            rank_txt = self._font_row.render(str(rank), True, rank_col)
            surf.blit(rank_txt, (cx + 14, y + 6))
            cx += _COLUMNS[0][2]

            try:
                color = tuple(int(c) for c in row["avatar_color"].split(","))
            except Exception:
                color = (212, 175, 55)
            draw_avatar(surf, row["avatar_shape"], color, cx + 16, y + row_h // 2 - 2, 14)
            name_txt = self._font_row.render(row["name"], True, cfg.COLOR_TEXT)
            surf.blit(name_txt, (cx + 38, y + 6))
            cx += _COLUMNS[1][2]

            surf.blit(self._font_row.render(f"{row['chips']:.0f}", True, cfg.COLOR_TEXT), (cx, y + 6))
            cx += _COLUMNS[2][2]

            surf.blit(self._font_row.render(str(row["hands_played"]), True, cfg.COLOR_TEXT), (cx, y + 6))
            cx += _COLUMNS[3][2]

            pct = row["win_pct"]
            pct_col = cfg.COLOR_WIN if pct >= 50 else (cfg.COLOR_TEXT if pct > 0 else (120, 120, 120))
            surf.blit(self._font_row.render(f"{pct:.0f}%", True, pct_col), (cx, y + 6))
            cx += _COLUMNS[4][2]

            surf.blit(self._font_row.render(str(row["blackjacks"]), True, cfg.COLOR_BJ), (cx, y + 6))
            cx += _COLUMNS[5][2]

            surf.blit(self._font_row.render(str(row["best_streak"]), True, cfg.COLOR_TEXT), (cx, y + 6))
            cx += _COLUMNS[6][2]

            ach_col = cfg.COLOR_GOLD if row["achievements"] == _TOTAL_ACHIEVEMENTS else cfg.COLOR_TEXT
            surf.blit(self._font_row.render(f"{row['achievements']}/{_TOTAL_ACHIEVEMENTS}", True, ach_col),
                      (cx, y + 6))

            y += row_h

    def _draw_sort_arrow(self, surf: pygame.Surface, x: int, y: int, desc: bool, color: tuple) -> None:
        s = 5
        if desc:
            pts = [(x - s, y - s // 2), (x + s, y - s // 2), (x, y + s)]
        else:
            pts = [(x - s, y + s), (x + s, y + s), (x, y - s)]
        pygame.draw.polygon(surf, color, pts)

    def _draw_back(self, surf: pygame.Surface) -> None:
        back_col = cfg.COLOR_GOLD if self._back_hover else (150, 150, 150)
        pygame.draw.rect(surf, (20, 15, 0), self._back_rect, border_radius=10)
        pygame.draw.rect(surf, back_col, self._back_rect, 2, border_radius=10)
        back_txt = self._font_row.render("Volver", True, back_col)
        surf.blit(back_txt, (self._back_rect.centerx - back_txt.get_width() // 2,
                              self._back_rect.centery - back_txt.get_height() // 2))
        hint = self._font_small.render("Esc/Volver para salir", True, (90, 90, 90))
        surf.blit(hint, (self.sw // 2 - hint.get_width() // 2, self.sh - 24))
