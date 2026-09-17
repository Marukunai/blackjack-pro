# ui/profile_select.py
# Pantalla "¿Quién juega?": selector de perfiles locales al arrancar.
#
# Solo nombre + avatar — sin contraseña, porque no hay nada que proteger
# ni nadie más que se conecte en un juego local de un solo jugador. Cada
# perfil guarda su propio progreso y estadísticas en saves/profiles.db
# (ver engine/profile_store.py), con historial completo por perfil.
# -------------------------------------------------------------
from __future__ import annotations

import pygame
from typing import Optional

from config import settings as cfg
from config import i18n
from engine.profile_store import get_store
from ui import icons
from ui.hand_history import HandHistoryScreen
# ui.leaderboard importa draw_avatar de este mismo módulo, así que se
# importa de forma diferida dentro de _show_leaderboard() para evitar un
# import circular a nivel de módulo.


# Paleta reducida de avatares: (forma, color). La forma reutiliza los
# iconos vectoriales ya existentes (palos de carta, estrella, ficha) en
# vez de depender de emoji que pueden no existir en la fuente del sistema.
AVATARS: list[tuple[str, tuple[int, int, int]]] = [
    ("S", (225, 225, 225)),
    ("H", (210, 70, 70)),
    ("D", (210, 70, 70)),
    ("C", (225, 225, 225)),
    ("star", (212, 175, 55)),
    ("coin", (212, 175, 55)),
    ("star", (100, 170, 230)),
    ("S", (100, 170, 230)),
]


def draw_avatar(surf: pygame.Surface, shape: str, color: tuple,
                 cx: int, cy: int, r: int) -> None:
    """Dibuja el icono de un avatar (círculo de fondo + símbolo), centrado."""
    cx, cy, r = int(cx), int(cy), int(r)
    bg = tuple(max(0, c - 165) for c in color)
    pygame.draw.circle(surf, bg, (cx, cy), r)
    pygame.draw.circle(surf, color, (cx, cy), r, 2)
    if shape == "star":
        icons.star(surf, cx, cy, r * 0.55, color)
    elif shape == "coin":
        font = pygame.font.SysFont(None, max(12, int(r * 1.3)), bold=True)
        icons.coin(surf, cx, cy, r * 0.62, color, (20, 20, 20), font)
    else:
        icons.draw_suit(surf, shape, cx, cy, r * 1.15, color)


class _Row:
    """Fila de un perfil existente en la lista."""
    def __init__(self, data: dict, rect: pygame.Rect, trash_rect: pygame.Rect,
                 hist_rect: pygame.Rect) -> None:
        self.data = data
        self.rect = rect
        self.trash_rect = trash_rect
        self.hist_rect = hist_rect
        self.hover = False
        self.trash_hover = False
        self.hist_hover = False


class ProfileSelect:
    """
    Pantalla previa al menú principal: elegir un perfil local existente
    o crear uno nuevo (nombre + avatar). Devuelve (profile_id, name)
    cuando el jugador confirma su elección.
    """

    def __init__(self, screen: pygame.Surface, exclude_ids: Optional[set] = None,
                 title: Optional[str] = None) -> None:
        self.screen = screen
        self.sw, self.sh = screen.get_size()
        self.store = get_store()
        # IDs a ocultar de la lista — perfiles que ya están sentados a la
        # mesa en esta sesión (multijugador local): la misma persona no
        # puede ocupar dos asientos a la vez.
        self._exclude_ids = exclude_ids or set()
        self._title_text = title or i18n.t("profile.title_default")

        self._font_title = pygame.font.SysFont(None, 48, bold=True)
        self._font_sub   = pygame.font.SysFont(None, 24, bold=True)
        self._font_body  = pygame.font.SysFont(None, 22)
        self._font_small = pygame.font.SysFont(None, 18)

        self._done = False
        self._result: Optional[tuple[int, str]] = None

        self._mode = "list"          # "list" | "create"
        self._confirm_delete_id: Optional[int] = None
        self._error_msg = ""

        # Creación de perfil
        self._name_input = ""
        self._avatar_idx = 0
        self._create_btn = pygame.Rect(0, 0, 0, 0)
        self._cancel_btn = pygame.Rect(0, 0, 0, 0)

        self._rows: list[_Row] = []
        self._new_rect: Optional[pygame.Rect] = None
        self._new_hover = False

        self._board_rect = pygame.Rect(self.sw - 190, 20, 170, 32)
        self._board_hover = False

        self._anim_offset = 0.0

        self._reload()

    # ------------------------------------------------------------------
    def _reload(self) -> None:
        self._profiles = [p for p in self.store.list_profiles()
                           if p["id"] not in self._exclude_ids]
        self._build_rows()

    def _build_rows(self) -> None:
        self._rows.clear()
        row_w, row_h, gap = 440, 56, 10
        top = 170
        x = self.sw // 2 - row_w // 2
        for i, data in enumerate(self._profiles):
            y = top + i * (row_h + gap)
            rect = pygame.Rect(x, y, row_w, row_h)
            trash = pygame.Rect(rect.right - 40, rect.y + row_h // 2 - 12, 24, 24)
            hist = pygame.Rect(rect.right - 76, rect.y + row_h // 2 - 12, 24, 24)
            self._rows.append(_Row(data, rect, trash, hist))
        y = top + len(self._profiles) * (row_h + gap)
        self._new_rect = pygame.Rect(x, y, row_w, row_h)

    # ------------------------------------------------------------------
    def run(self) -> tuple[int, str]:
        """Bucle bloqueante. Devuelve (profile_id, nombre)."""
        clock = pygame.time.Clock()
        while not self._done:
            clock.tick(60)
            self._anim_offset += 0.3
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit
                self._handle_event(event)
            self._draw()
            pygame.display.flip()
        return self._result

    # ------------------------------------------------------------------
    # Eventos
    # ------------------------------------------------------------------
    def _handle_event(self, event: pygame.event.Event) -> None:
        if self._mode == "list":
            self._handle_list_event(event)
        else:
            self._handle_create_event(event)

    def _handle_list_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            for row in self._rows:
                row.hover = row.rect.collidepoint(event.pos)
                row.trash_hover = row.trash_rect.collidepoint(event.pos)
                row.hist_hover = row.hist_rect.collidepoint(event.pos)
            if self._new_rect:
                self._new_hover = self._new_rect.collidepoint(event.pos)
            self._board_hover = self._board_rect.collidepoint(event.pos)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._board_rect.collidepoint(event.pos) and len(self._profiles) >= 1:
                self._show_leaderboard()
                return
            for i, row in enumerate(self._rows):
                if row.hist_rect.collidepoint(event.pos):
                    self._show_history(i)
                    return
                if row.trash_rect.collidepoint(event.pos):
                    if self._confirm_delete_id == row.data["id"]:
                        self.store.delete_profile(row.data["id"])
                        self._confirm_delete_id = None
                        self._reload()
                    else:
                        self._confirm_delete_id = row.data["id"]
                    return
                if row.rect.collidepoint(event.pos):
                    self._select(row.data)
                    return
            if self._new_rect and self._new_rect.collidepoint(event.pos):
                self._enter_create_mode()
                return
            # Click fuera de cualquier fila: cancela un borrado pendiente de confirmar
            self._confirm_delete_id = None

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN and self._profiles:
                self._select(self._profiles[0])
            elif event.key == pygame.K_n:
                self._enter_create_mode()

    def _enter_create_mode(self) -> None:
        self._mode = "create"
        self._name_input = ""
        self._avatar_idx = 0
        self._error_msg = ""
        self._confirm_delete_id = None

    def _select(self, data: dict) -> None:
        self.store.touch(data["id"])
        self._result = (data["id"], data["name"])
        self._done = True

    def _show_history(self, row_index: int) -> None:
        """Abre el historial de manos de un perfil sin seleccionarlo para
        jugar. Se le pasan TODOS los perfiles visibles en la lista, así
        que desde dentro se puede saltar al historial de cualquier otro
        con Tab, no solo el que se clickeó."""
        profiles = [(r.data["id"], r.data["name"]) for r in self._rows]
        HandHistoryScreen(self.screen, profiles, initial_index=row_index).run()
        self._confirm_delete_id = None

    def _show_leaderboard(self) -> None:
        from ui.leaderboard import LeaderboardScreen  # import diferido, ver arriba
        LeaderboardScreen(self.screen).run()
        self._confirm_delete_id = None

    def _handle_create_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._mode = "list"
            elif event.key == pygame.K_BACKSPACE:
                self._name_input = self._name_input[:-1]
            elif event.key == pygame.K_RETURN:
                self._confirm_create()
            elif event.key == pygame.K_LEFT:
                self._avatar_idx = (self._avatar_idx - 1) % len(AVATARS)
            elif event.key == pygame.K_RIGHT:
                self._avatar_idx = (self._avatar_idx + 1) % len(AVATARS)
            elif len(self._name_input) < 16 and event.unicode.isprintable():
                self._name_input += event.unicode

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, r in enumerate(self._avatar_rects()):
                if r.collidepoint(event.pos):
                    self._avatar_idx = i
                    return
            if self._create_btn.collidepoint(event.pos):
                self._confirm_create()
                return
            if self._cancel_btn.collidepoint(event.pos):
                self._mode = "list"
                return

    def _confirm_create(self) -> None:
        name = self._name_input.strip()
        if not name:
            self._error_msg = i18n.t("profile.error_empty_name")
            return
        shape, color = AVATARS[self._avatar_idx]
        try:
            pid = self.store.create_profile(name, shape, color)
        except ValueError as e:
            self._error_msg = str(e)
            return
        self._select({"id": pid, "name": name})

    # ------------------------------------------------------------------
    def _avatar_rects(self) -> list[pygame.Rect]:
        cols = 4
        size, gap = 64, 14
        total_w = cols * size + (cols - 1) * gap
        x0 = self.sw // 2 - total_w // 2
        y0 = self.sh // 2 - 10
        rects = []
        for i in range(len(AVATARS)):
            col, row = i % cols, i // cols
            x = x0 + col * (size + gap)
            y = y0 + row * (size + gap)
            rects.append(pygame.Rect(x, y, size, size))
        return rects

    # ------------------------------------------------------------------
    # Dibujo
    # ------------------------------------------------------------------
    def _draw(self) -> None:
        surf = self.screen
        surf.fill(cfg.COLOR_BG)
        if self._mode == "list":
            self._draw_list(surf)
        else:
            self._draw_create(surf)

    def _draw_list(self, surf: pygame.Surface) -> None:
        title = self._font_title.render(self._title_text, True, cfg.COLOR_GOLD)
        surf.blit(title, (self.sw // 2 - title.get_width() // 2, 60))
        sub_text = (i18n.t("profile.subtitle_default")
                    if not self._exclude_ids else
                    i18n.t("profile.subtitle_seat"))
        sub = self._font_small.render(sub_text, True, (150, 150, 150))
        surf.blit(sub, (self.sw // 2 - sub.get_width() // 2, 112))

        if self._profiles:
            bg = (255, 255, 255, 22) if self._board_hover else (255, 255, 255, 10)
            box = pygame.Surface((self._board_rect.w, self._board_rect.h), pygame.SRCALPHA)
            pygame.draw.rect(box, bg, box.get_rect(), border_radius=8)
            pygame.draw.rect(box, cfg.COLOR_GOLD if self._board_hover else (110, 110, 110),
                              box.get_rect(), 1, border_radius=8)
            surf.blit(box, (self._board_rect.x, self._board_rect.y))
            board_col = cfg.COLOR_GOLD if self._board_hover else (200, 200, 200)
            icons.bars_icon(surf, self._board_rect.x + 20, self._board_rect.centery, 13, board_col)
            board_txt = self._font_small.render(i18n.t("profile.leaderboard_button"), True, board_col)
            surf.blit(board_txt, (self._board_rect.x + 36, self._board_rect.centery - board_txt.get_height() // 2))

        for row in self._rows:
            self._draw_row(surf, row)

        if self._new_rect:
            bg = (255, 255, 255, 22) if self._new_hover else (255, 255, 255, 8)
            box = pygame.Surface((self._new_rect.w, self._new_rect.h), pygame.SRCALPHA)
            pygame.draw.rect(box, bg, box.get_rect(), border_radius=10)
            pygame.draw.rect(box, cfg.COLOR_GOLD if self._new_hover else (110, 110, 110),
                              box.get_rect(), 1, border_radius=10)
            surf.blit(box, (self._new_rect.x, self._new_rect.y))
            plus = self._font_sub.render(i18n.t("profile.new_profile_button"), True,
                                          cfg.COLOR_GOLD if self._new_hover else (200, 200, 200))
            surf.blit(plus, (self._new_rect.centerx - plus.get_width() // 2,
                              self._new_rect.centery - plus.get_height() // 2))

        hint = self._font_small.render(i18n.t("profile.list_hint"), True, (90, 90, 90))
        surf.blit(hint, (self.sw // 2 - hint.get_width() // 2, self.sh - 28))

    def _draw_row(self, surf: pygame.Surface, row: "_Row") -> None:
        r = row.rect
        bg = (255, 255, 255, 26) if row.hover else (255, 255, 255, 10)
        box = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
        pygame.draw.rect(box, bg, box.get_rect(), border_radius=10)
        pygame.draw.rect(box, cfg.COLOR_GOLD if row.hover else (90, 90, 90),
                          box.get_rect(), 1, border_radius=10)
        surf.blit(box, (r.x, r.y))

        data = row.data
        try:
            color = tuple(int(c) for c in data["avatar_color"].split(","))
        except Exception:
            color = (212, 175, 55)
        draw_avatar(surf, data.get("avatar_shape", "S"), color, r.x + 32, r.centery, 20)

        confirming = (self._confirm_delete_id == data["id"])

        name = self._font_body.render(data["name"], True, cfg.COLOR_TEXT)
        surf.blit(name, (r.x + 64, r.y + 8))
        # Mientras se confirma el borrado, la línea de info se reemplaza
        # por el aviso -- en vez de superponer texto extra a la derecha,
        # que pisaba el icono de historial recién añadido.
        if confirming:
            info = self._font_small.render(i18n.t("profile.confirm_delete"), True, cfg.COLOR_LOSE)
        else:
            info = self._font_small.render(
                i18n.t("profile.chips_hands_info", chips=data["chips"], hands=data["hands_played"]),
                True, (150, 150, 150))
        surf.blit(info, (r.x + 64, r.y + 30))

        h = row.hist_rect
        hist_col = cfg.COLOR_GOLD if row.hist_hover else (110, 110, 110)
        icons.list_icon(surf, h.centerx, h.centery, 13, hist_col, width=2)

        t = row.trash_rect
        trash_col = cfg.COLOR_LOSE if (row.trash_hover or confirming) else (110, 110, 110)
        icons.cross_mark(surf, t.centerx, t.centery, 14, trash_col, width=2)

    def _draw_create(self, surf: pygame.Surface) -> None:
        title = self._font_title.render(i18n.t("profile.create_title"), True, cfg.COLOR_GOLD)
        surf.blit(title, (self.sw // 2 - title.get_width() // 2, 60))

        name_rect = pygame.Rect(self.sw // 2 - 150, 150, 300, 36)
        label = self._font_body.render(i18n.t("profile.name_label"), True, cfg.COLOR_TEXT)
        surf.blit(label, (name_rect.x, name_rect.y - 24))
        pygame.draw.rect(surf, (20, 20, 20), name_rect, border_radius=6)
        pygame.draw.rect(surf, cfg.COLOR_GOLD, name_rect, 1, border_radius=6)
        disp = self._name_input + "|"
        name_surf = self._font_body.render(disp, True, cfg.COLOR_TEXT)
        surf.blit(name_surf, (name_rect.x + 8, name_rect.y + 8))

        avatar_lbl = self._font_body.render(i18n.t("profile.avatar_label"), True, cfg.COLOR_TEXT)
        surf.blit(avatar_lbl, (self.sw // 2 - avatar_lbl.get_width() // 2, self.sh // 2 - 46))

        for i, r in enumerate(self._avatar_rects()):
            shape, color = AVATARS[i]
            if i == self._avatar_idx:
                pygame.draw.rect(surf, cfg.COLOR_GOLD, r.inflate(6, 6), 2, border_radius=12)
            draw_avatar(surf, shape, color, r.centerx, r.centery, r.w // 2 - 4)

        btn_y = self.sh - 110
        self._create_btn = pygame.Rect(self.sw // 2 - 130, btn_y, 120, 44)
        self._cancel_btn = pygame.Rect(self.sw // 2 + 10, btn_y, 120, 44)

        pygame.draw.rect(surf, (20, 15, 0), self._create_btn, border_radius=10)
        pygame.draw.rect(surf, cfg.COLOR_GOLD, self._create_btn, 2, border_radius=10)
        c_txt = self._font_sub.render(i18n.t("profile.create_button"), True, cfg.COLOR_GOLD)
        surf.blit(c_txt, (self._create_btn.centerx - c_txt.get_width() // 2,
                           self._create_btn.centery - c_txt.get_height() // 2))

        pygame.draw.rect(surf, (20, 20, 20), self._cancel_btn, border_radius=10)
        pygame.draw.rect(surf, (120, 120, 120), self._cancel_btn, 1, border_radius=10)
        x_txt = self._font_sub.render(i18n.t("profile.cancel_button"), True, (180, 180, 180))
        surf.blit(x_txt, (self._cancel_btn.centerx - x_txt.get_width() // 2,
                           self._cancel_btn.centery - x_txt.get_height() // 2))

        if self._error_msg:
            err = self._font_small.render(self._error_msg, True, cfg.COLOR_LOSE)
            surf.blit(err, (self.sw // 2 - err.get_width() // 2, btn_y - 26))

        hint = self._font_small.render(i18n.t("profile.create_hint"), True, (90, 90, 90))
        surf.blit(hint, (self.sw // 2 - hint.get_width() // 2, self.sh - 28))


class SeatConfirmScreen:
    """
    Pantalla intermedia del "lobby" multijugador: tras elegir un perfil
    para un asiento, pregunta si se añade otro jugador (hasta 3) o se
    empieza ya a jugar con los que hay sentados. Así ProfileSelect no
    necesita saber nada de selección múltiple — solo elige UN perfil cada
    vez que se invoca, y esta pantalla encadena las llamadas.
    """

    MAX_SEATS = 3

    def __init__(self, screen: pygame.Surface, seats: list[tuple[int, str]]) -> None:
        self.screen = screen
        self.sw, self.sh = screen.get_size()
        self.seats = seats
        self.store = get_store()

        self._font_title = pygame.font.SysFont(None, 40, bold=True)
        self._font_seat  = pygame.font.SysFont(None, 24, bold=True)
        self._font_small = pygame.font.SysFont(None, 18)

        self._done = False
        self._result = False   # True = añadir otro · False = empezar a jugar

        self._add_btn = pygame.Rect(0, 0, 0, 0)
        self._play_btn = pygame.Rect(0, 0, 0, 0)
        self._add_hover = False
        self._play_hover = False

    def run(self) -> bool:
        """Bucle bloqueante. Devuelve True si hay que añadir otro jugador,
        False si hay que empezar a jugar con los ya sentados."""
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
        return self._result

    def _handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            self._add_hover = self._add_btn.collidepoint(event.pos)
            self._play_hover = self._play_btn.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._add_hover and len(self.seats) < self.MAX_SEATS:
                self._result = True
                self._done = True
            elif self._play_btn.collidepoint(event.pos):
                self._result = False
                self._done = True
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self._result = False
                self._done = True
            elif event.key in (pygame.K_a, pygame.K_PLUS) and len(self.seats) < self.MAX_SEATS:
                self._result = True
                self._done = True

    def _draw(self) -> None:
        surf = self.screen
        surf.fill(cfg.COLOR_BG)

        title = self._font_title.render(i18n.t("profile.seats_title"), True, cfg.COLOR_GOLD)
        surf.blit(title, (self.sw // 2 - title.get_width() // 2, 70))

        # Fila de asientos ya confirmados
        row_w, row_h, gap = 260, 64, 16
        total_w = len(self.seats) * row_w + (len(self.seats) - 1) * gap
        x0 = self.sw // 2 - total_w // 2
        y0 = 180
        data_by_id = {p["id"]: p for p in self.store.list_profiles()}
        for i, (pid, name) in enumerate(self.seats):
            r = pygame.Rect(x0 + i * (row_w + gap), y0, row_w, row_h)
            box = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
            pygame.draw.rect(box, (255, 255, 255, 14), box.get_rect(), border_radius=10)
            pygame.draw.rect(box, cfg.COLOR_GOLD, box.get_rect(), 1, border_radius=10)
            surf.blit(box, (r.x, r.y))

            data = data_by_id.get(pid, {})
            try:
                color = tuple(int(c) for c in data.get("avatar_color", "212,175,55").split(","))
            except Exception:
                color = (212, 175, 55)
            draw_avatar(surf, data.get("avatar_shape", "S"), color, r.x + 32, r.centery, 20)

            lbl = self._font_seat.render(name, True, cfg.COLOR_TEXT)
            surf.blit(lbl, (r.x + 60, r.y + 12))
            sub = self._font_small.render(i18n.t("profile.seat_number", n=i + 1), True, (150, 150, 150))
            surf.blit(sub, (r.x + 60, r.y + 36))

        btn_y = y0 + row_h + 60
        can_add = len(self.seats) < self.MAX_SEATS

        if can_add:
            self._add_btn = pygame.Rect(self.sw // 2 - 260, btn_y, 240, 52)
            col = cfg.COLOR_GOLD if self._add_hover else (140, 115, 40)
            pygame.draw.rect(surf, (20, 15, 0), self._add_btn, border_radius=10)
            pygame.draw.rect(surf, col, self._add_btn, 2, border_radius=10)
            t = self._font_seat.render(i18n.t("profile.add_player_button"), True, col)
            surf.blit(t, (self._add_btn.centerx - t.get_width() // 2,
                          self._add_btn.centery - t.get_height() // 2))
        else:
            self._add_btn = pygame.Rect(0, 0, 0, 0)
            note = self._font_small.render(i18n.t("profile.max_players_note"), True, (120, 120, 120))
            surf.blit(note, (self.sw // 2 - 260 + 120 - note.get_width() // 2, btn_y + 18))

        self._play_btn = pygame.Rect(self.sw // 2 + 20, btn_y, 240, 52)
        col2 = cfg.COLOR_GOLD if self._play_hover else (140, 115, 40)
        pygame.draw.rect(surf, (20, 15, 0), self._play_btn, border_radius=10)
        pygame.draw.rect(surf, col2, self._play_btn, 2, border_radius=10)
        label = i18n.t("profile.play_button") if len(self.seats) > 1 else i18n.t("profile.play_solo_button")
        t2 = self._font_seat.render(label, True, col2)
        icons.triangle_right(surf, self._play_btn.centerx - t2.get_width() // 2 - 22,
                              self._play_btn.centery, 12, col2)
        surf.blit(t2, (self._play_btn.centerx - t2.get_width() // 2,
                       self._play_btn.centery - t2.get_height() // 2))

        hint = self._font_small.render(
            i18n.t("profile.seats_hint_play") + (i18n.t("profile.seats_hint_add") if can_add else ""),
            True, (90, 90, 90))
        surf.blit(hint, (self.sw // 2 - hint.get_width() // 2, self.sh - 28))
