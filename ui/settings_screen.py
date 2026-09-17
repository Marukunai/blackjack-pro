# ui/settings_screen.py
# Pantalla de "Ajustes": temas visuales (mesa y reverso de cartas, Fase
# 15) y volumen de audio (Fase 16). Los cambios se aplican al instante
# (config/settings.py, ver apply_table_theme/apply_card_back_theme) y se
# persisten en saves/app_settings.json (engine/app_settings.py) para que
# sobrevivan al reinicio. ui/renderer.py invalida los cachés de mesa/
# cartas cada vez que se vuelve del menú, así que aquí no hace falta
# preocuparse por refrescar nada fuera de esta pantalla.
# -------------------------------------------------------------
from __future__ import annotations

from typing import Optional

import pygame

from config import settings as cfg
from config import i18n
from engine.app_settings import get_settings
from ui import icons

_SWATCH_W, _SWATCH_H = 160, 90
_SWATCH_GAP = 20

_TRACK_W, _TRACK_H = 260, 6
_KNOB_R = 8


class SettingsScreen:
    """Pantalla de solo-preferencias: sin "Guardar"/"Cancelar" -- cada
    click aplica y persiste al instante (igual que elegir un avatar), y
    Volver/Esc simplemente cierra. Bucle bloqueante.

    `sounds`, si se pasa (la instancia real de ui.sounds.SoundManager que
    ya está sonando en el menú), permite que el volumen cambie AL
    INSTANTE mientras se arrastra el slider -- si es None (p. ej. algún
    test), los ajustes se aplican y persisten igual, solo que sin preview
    en vivo desde aquí."""

    def __init__(self, screen: pygame.Surface, sounds=None) -> None:
        self.screen = screen
        self.sw, self.sh = screen.get_size()
        self.app_settings = get_settings()
        self._sounds = sounds

        self._font_title = pygame.font.SysFont(None, 38, bold=True)
        self._font_section = pygame.font.SysFont(None, 22, bold=True)
        self._font_label = pygame.font.SysFont(None, 18, bold=True)
        self._font_small = pygame.font.SysFont(None, 16)

        self._done = False
        self._back_rect = pygame.Rect(self.sw // 2 - 90, self.sh - 78, 180, 44)
        self._back_hover = False

        self._table_rects: list[tuple[str, pygame.Rect]] = []
        self._back_card_rects: list[tuple[str, pygame.Rect]] = []
        self._layout()

        # ---- Estado de audio (Fase 16) ----
        # None persistido = "nunca se tocó desde Ajustes" -> 100% / activado,
        # que es como suena el juego de toda la vida sin pasar por aquí.
        self._music_vol = self.app_settings.get("music_volume")
        self._music_vol = 1.0 if self._music_vol is None else float(self._music_vol)
        self._sfx_vol = self.app_settings.get("sfx_volume")
        self._sfx_vol = 1.0 if self._sfx_vol is None else float(self._sfx_vol)
        me = self.app_settings.get("music_enabled")
        self._music_on = True if me is None else bool(me)
        se = self.app_settings.get("sfx_enabled")
        self._sfx_on = True if se is None else bool(se)

        self._dragging: Optional[str] = None   # "music" | "sfx" | None
        self._music_mute_rect = pygame.Rect(0, 0, 0, 0)
        self._sfx_mute_rect = pygame.Rect(0, 0, 0, 0)
        self._music_mute_hover = False
        self._sfx_mute_hover = False
        self._layout_audio()

        # ---- Idioma (Fase 26) ----
        # Un simple par de botones ES/EN en la esquina superior derecha
        # (no un swatch grid como mesa/cartas -- solo hay 2 opciones) que
        # cambian cfg.LANGUAGE al instante y se persisten igual que el
        # resto de ajustes. Al ser un valor "en vivo" leído por i18n.t()
        # en cada frame, el resto de esta misma pantalla (y de cualquier
        # otra) ya sale traducida sin más que redibujar.
        self._lang = cfg.LANGUAGE if cfg.LANGUAGE in ("es", "en") else "es"
        lang_w, lang_h = 64, 30
        self._lang_es_rect = pygame.Rect(self.sw - 158, 22, lang_w, lang_h)
        self._lang_en_rect = pygame.Rect(self.sw - 88, 22, lang_w, lang_h)
        self._lang_es_hover = False
        self._lang_en_hover = False

    # ------------------------------------------------------------------
    def _layout(self) -> None:
        table_names = list(cfg.TABLE_THEMES.keys())
        row1_y = 170
        total_w = len(table_names) * _SWATCH_W + (len(table_names) - 1) * _SWATCH_GAP
        x0 = self.sw // 2 - total_w // 2
        self._table_rects = []
        for i, name in enumerate(table_names):
            r = pygame.Rect(x0 + i * (_SWATCH_W + _SWATCH_GAP), row1_y, _SWATCH_W, _SWATCH_H)
            self._table_rects.append((name, r))
        self._row1_y = row1_y

        back_names = list(cfg.CARD_BACK_THEMES.keys())
        row2_y = 380
        total_w2 = len(back_names) * _SWATCH_W + (len(back_names) - 1) * _SWATCH_GAP
        x0b = self.sw // 2 - total_w2 // 2
        self._back_card_rects = []
        for i, name in enumerate(back_names):
            r = pygame.Rect(x0b + i * (_SWATCH_W + _SWATCH_GAP), row2_y, _SWATCH_W, _SWATCH_H)
            self._back_card_rects.append((name, r))
        self._row2_y = row2_y

    def _layout_audio(self) -> None:
        self._row3_y = self._row2_y + _SWATCH_H + 90   # etiqueta de sección "Audio"
        track_x = self.sw // 2 - _TRACK_W // 2
        self._music_row_y = self._row3_y + 38
        self._sfx_row_y = self._music_row_y + 50
        self._music_track = pygame.Rect(track_x, self._music_row_y, _TRACK_W, _TRACK_H)
        self._sfx_track = pygame.Rect(track_x, self._sfx_row_y, _TRACK_W, _TRACK_H)
        self._music_mute_rect = pygame.Rect(track_x - 118, self._music_row_y - 9, 24, 24)
        self._sfx_mute_rect = pygame.Rect(track_x - 118, self._sfx_row_y - 9, 24, 24)

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
            self._music_mute_hover = self._music_mute_rect.collidepoint(event.pos)
            self._sfx_mute_hover = self._sfx_mute_rect.collidepoint(event.pos)
            self._lang_es_hover = self._lang_es_rect.collidepoint(event.pos)
            self._lang_en_hover = self._lang_en_rect.collidepoint(event.pos)
            if self._dragging == "music":
                self._set_music_volume(self._value_from_x(self._music_track, event.pos[0]))
            elif self._dragging == "sfx":
                self._set_sfx_volume(self._value_from_x(self._sfx_track, event.pos[0]))

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._dragging is not None:
                self._dragging = None
                self.app_settings.set("music_volume", self._music_vol)
                self.app_settings.set("sfx_volume", self._sfx_vol)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._back_rect.collidepoint(event.pos):
                self._done = True
                return
            if self._lang_es_rect.collidepoint(event.pos):
                self._choose_language("es")
                return
            if self._lang_en_rect.collidepoint(event.pos):
                self._choose_language("en")
                return
            for name, r in self._table_rects:
                if r.collidepoint(event.pos):
                    self._choose_table_theme(name)
                    return
            for name, r in self._back_card_rects:
                if r.collidepoint(event.pos):
                    self._choose_card_back(name)
                    return
            if self._music_mute_rect.collidepoint(event.pos):
                self._toggle_music_enabled()
                return
            if self._sfx_mute_rect.collidepoint(event.pos):
                self._toggle_sfx_enabled()
                return
            if self._hit_track(self._music_track).collidepoint(event.pos):
                self._dragging = "music"
                self._set_music_volume(self._value_from_x(self._music_track, event.pos[0]))
                return
            if self._hit_track(self._sfx_track).collidepoint(event.pos):
                self._dragging = "sfx"
                self._set_sfx_volume(self._value_from_x(self._sfx_track, event.pos[0]))
                return

    def _choose_table_theme(self, name: str) -> None:
        if cfg.apply_table_theme(name):
            self.app_settings.set("table_theme", name)

    def _choose_card_back(self, name: str) -> None:
        if cfg.apply_card_back_theme(name):
            self.app_settings.set("card_back_theme", name)

    def _choose_language(self, lang: str) -> None:
        if lang not in ("es", "en") or lang == self._lang:
            return
        self._lang = lang
        cfg.LANGUAGE = lang
        self.app_settings.set("language", lang)

    # ------------------------------------------------------------------
    # Audio (Fase 16)
    # ------------------------------------------------------------------
    @staticmethod
    def _hit_track(track: pygame.Rect) -> pygame.Rect:
        """Zona clicable de un slider -- más alta que la barra visible
        (6px) para que no haga falta apuntar con precisión de píxel."""
        return track.inflate(_KNOB_R * 2, 20)

    @staticmethod
    def _value_from_x(track: pygame.Rect, x: int) -> float:
        return max(0.0, min(1.0, (x - track.x) / track.w))

    def _set_music_volume(self, v: float) -> None:
        self._music_vol = v
        if self._sounds is not None:
            self._sounds.set_music_volume(v)

    def _set_sfx_volume(self, v: float) -> None:
        self._sfx_vol = v
        if self._sounds is not None:
            self._sounds.set_sfx_volume(v)

    def _toggle_music_enabled(self) -> None:
        self._music_on = not self._music_on
        if self._sounds is not None:
            self._sounds.set_music_enabled(self._music_on)
        self.app_settings.set("music_enabled", self._music_on)

    def _toggle_sfx_enabled(self) -> None:
        self._sfx_on = not self._sfx_on
        if self._sounds is not None:
            self._sounds.set_sfx_enabled(self._sfx_on)
        self.app_settings.set("sfx_enabled", self._sfx_on)

    # ------------------------------------------------------------------
    # Dibujo
    # ------------------------------------------------------------------
    def _draw(self) -> None:
        surf = self.screen
        surf.fill(cfg.COLOR_BG)

        title = self._font_title.render(i18n.t("menu.settings_button"), True, cfg.COLOR_GOLD)
        surf.blit(title, (self.sw // 2 - title.get_width() // 2, 50))

        self._draw_language_toggle(surf)

        sect1 = self._font_section.render(i18n.t("settings.table_section"), True, cfg.COLOR_TEXT)
        surf.blit(sect1, (self.sw // 2 - sect1.get_width() // 2, self._row1_y - 34))
        for name, r in self._table_rects:
            self._draw_table_swatch(surf, name, r)

        sect2 = self._font_section.render(i18n.t("settings.card_back_section"), True, cfg.COLOR_TEXT)
        surf.blit(sect2, (self.sw // 2 - sect2.get_width() // 2, self._row2_y - 34))
        for name, r in self._back_card_rects:
            self._draw_card_back_swatch(surf, name, r)

        sect3 = self._font_section.render(i18n.t("settings.audio_section"), True, cfg.COLOR_TEXT)
        surf.blit(sect3, (self.sw // 2 - sect3.get_width() // 2, self._row3_y - 34))
        self._draw_audio_row(surf, i18n.t("settings.music_label"), self._music_track, self._music_mute_rect,
                              self._music_vol, self._music_on, self._music_mute_hover)
        self._draw_audio_row(surf, i18n.t("settings.sfx_label"), self._sfx_track, self._sfx_mute_rect,
                              self._sfx_vol, self._sfx_on, self._sfx_mute_hover)

        self._draw_back(surf)

    def _draw_language_toggle(self, surf: pygame.Surface) -> None:
        lbl = self._font_small.render(i18n.t("settings.language_section"), True, (140, 140, 140))
        surf.blit(lbl, (self._lang_es_rect.x - lbl.get_width() - 10,
                         self._lang_es_rect.centery - lbl.get_height() // 2))
        for lang, rect, hover, text in (
            ("es", self._lang_es_rect, self._lang_es_hover, "ES"),
            ("en", self._lang_en_rect, self._lang_en_hover, "EN"),
        ):
            active = (lang == self._lang)
            if active:
                bg, border, col = (60, 45, 10), cfg.COLOR_GOLD, cfg.COLOR_GOLD
            else:
                bg = (20, 15, 0)
                border = cfg.COLOR_GOLD if hover else (110, 110, 110)
                col = (220, 220, 220) if hover else (150, 150, 150)
            pygame.draw.rect(surf, bg, rect, border_radius=8)
            pygame.draw.rect(surf, border, rect, 2 if active else 1, border_radius=8)
            t = self._font_label.render(text, True, col)
            surf.blit(t, (rect.centerx - t.get_width() // 2, rect.centery - t.get_height() // 2))

    def _draw_audio_row(self, surf: pygame.Surface, label: str, track: pygame.Rect,
                         mute_rect: pygame.Rect, vol: float, on: bool, mute_hover: bool) -> None:
        col = cfg.COLOR_TEXT if on else (100, 100, 100)

        # Botón de silenciar/activar -- altavoz simple: triángulo + cuerpo.
        mcol = cfg.COLOR_GOLD if mute_hover else col
        pygame.draw.circle(surf, (255, 255, 255, 10), mute_rect.center, 13)
        pygame.draw.circle(surf, mcol, mute_rect.center, 13, 1)
        cx, cy = mute_rect.center
        pygame.draw.polygon(surf, mcol, [
            (cx - 6, cy - 3), (cx - 2, cy - 3), (cx + 3, cy - 7),
            (cx + 3, cy + 7), (cx - 2, cy + 3), (cx - 6, cy + 3),
        ])
        if not on:
            pygame.draw.line(surf, cfg.COLOR_LOSE, (cx - 7, cy - 7), (cx + 8, cy + 8), 2)

        lbl = self._font_label.render(label, True, col)
        surf.blit(lbl, (mute_rect.right + 12, track.centery - lbl.get_height() // 2))

        # Track + relleno + pomo
        pygame.draw.rect(surf, (60, 60, 60), track, border_radius=3)
        if on and vol > 0:
            fill = pygame.Rect(track.x, track.y, int(track.w * vol), track.h)
            pygame.draw.rect(surf, cfg.COLOR_GOLD, fill, border_radius=3)
        knob_x = track.x + int(track.w * vol)
        knob_col = cfg.COLOR_GOLD if on else (120, 120, 120)
        pygame.draw.circle(surf, knob_col, (knob_x, track.centery), _KNOB_R)
        pygame.draw.circle(surf, (20, 20, 20), (knob_x, track.centery), _KNOB_R, 1)

        pct = self._font_small.render(f"{int(round(vol * 100))}%" if on else i18n.t("settings.muted"),
                                       True, col)
        surf.blit(pct, (track.right + 14, track.centery - pct.get_height() // 2))

    def _draw_table_swatch(self, surf: pygame.Surface, name: str, r: pygame.Rect) -> None:
        theme = cfg.TABLE_THEMES[name]
        active = (name == cfg.CURRENT_TABLE_THEME)

        pygame.draw.rect(surf, theme["felt"], r, border_radius=10)
        pygame.draw.rect(surf, theme["felt_light"], r.inflate(-16, -16), 1, border_radius=8)
        border_col = cfg.COLOR_GOLD if active else (90, 90, 90)
        pygame.draw.rect(surf, border_col, r, 2, border_radius=10)

        if active:
            check_bg = pygame.Rect(0, 0, 22, 22)
            check_bg.topright = (r.right - 6, r.top + 6)
            pygame.draw.circle(surf, cfg.COLOR_GOLD, check_bg.center, 11)
            icons.check_mark(surf, *check_bg.center, 11, (20, 20, 20), width=2)

        lbl = self._font_label.render(i18n.table_theme_label(name, theme["label"]), True, cfg.COLOR_TEXT)
        surf.blit(lbl, (r.centerx - lbl.get_width() // 2, r.bottom + 8))

    def _draw_card_back_swatch(self, surf: pygame.Surface, name: str, r: pygame.Rect) -> None:
        theme = cfg.CARD_BACK_THEMES[name]
        active = (name == cfg.CURRENT_CARD_BACK_THEME)

        pygame.draw.rect(surf, (30, 30, 30), r, border_radius=10)

        card_w, card_h = 46, 64
        card_rect = pygame.Rect(0, 0, card_w, card_h)
        card_rect.center = r.center
        pygame.draw.rect(surf, theme["dark"], card_rect, border_radius=5)
        step = 12
        pat = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        for x in range(-card_h, card_w + card_h, step):
            pts = [(x, 0), (x + step // 2, card_h // 2), (x, card_h), (x - step // 2, card_h // 2)]
            pygame.draw.polygon(pat, theme["pattern"], pts, 1)
        surf.blit(pat, card_rect.topleft)
        pygame.draw.rect(surf, cfg.COLOR_GOLD, card_rect, 1, border_radius=5)

        border_col = cfg.COLOR_GOLD if active else (90, 90, 90)
        pygame.draw.rect(surf, border_col, r, 2, border_radius=10)

        if active:
            check_bg = pygame.Rect(0, 0, 22, 22)
            check_bg.topright = (r.right - 6, r.top + 6)
            pygame.draw.circle(surf, cfg.COLOR_GOLD, check_bg.center, 11)
            icons.check_mark(surf, *check_bg.center, 11, (20, 20, 20), width=2)

        lbl = self._font_label.render(i18n.card_back_label(name, theme["label"]), True, cfg.COLOR_TEXT)
        surf.blit(lbl, (r.centerx - lbl.get_width() // 2, r.bottom + 8))

    def _draw_back(self, surf: pygame.Surface) -> None:
        back_col = cfg.COLOR_GOLD if self._back_hover else (150, 150, 150)
        pygame.draw.rect(surf, (20, 15, 0), self._back_rect, border_radius=10)
        pygame.draw.rect(surf, back_col, self._back_rect, 2, border_radius=10)
        back_txt = self._font_label.render(i18n.t("menu.back_button"), True, back_col)
        surf.blit(back_txt, (self._back_rect.centerx - back_txt.get_width() // 2,
                              self._back_rect.centery - back_txt.get_height() // 2))
        hint = self._font_small.render(i18n.t("settings.hint"), True, (90, 90, 90))
        surf.blit(hint, (self.sw // 2 - hint.get_width() // 2, self.sh - 24))
