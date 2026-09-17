# ui/menu.py
# Menú principal, pantalla de configuración y selección de preset.
# -------------------------------------------------------------
from __future__ import annotations

import pygame
from typing import Optional, Callable
from config import settings as cfg
from config import i18n
from config.rules_presets import PRESETS, get_preset, vegas_strip
from core.rules import Rules, DealerRule, BlackjackPayout, DoubleRule, SurrenderRule
from engine.challenges import Challenge
from ui import icons
from ui.hand_history import HandHistoryScreen


class MenuItem:
    def __init__(self, text: str, value: str, x: int, y: int, w: int, h: int,
                 font: pygame.font.Font, selected: bool = False) -> None:
        self.text     = text
        self.value    = value
        self.rect     = pygame.Rect(x, y, w, h)
        self.font     = font
        self.selected = selected
        self._hover   = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            self._hover = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True
        return False

    def draw(self, surf: pygame.Surface) -> None:
        if self.selected:
            bg = (212, 175, 55, 40)
            border = cfg.COLOR_GOLD
            text_col = cfg.COLOR_GOLD
        elif self._hover:
            bg = (255, 255, 255, 20)
            border = (200, 200, 200)
            text_col = (255, 255, 255)
        else:
            bg = (0, 0, 0, 0)
            border = (100, 100, 100)
            text_col = (200, 200, 200)

        box = pygame.Surface((self.rect.w, self.rect.h), pygame.SRCALPHA)
        pygame.draw.rect(box, bg, box.get_rect(), border_radius=8)
        pygame.draw.rect(box, border, box.get_rect(), 1, border_radius=8)
        surf.blit(box, (self.rect.x, self.rect.y))

        t = self.font.render(self.text, True, text_col)
        surf.blit(t, (self.rect.centerx - t.get_width()//2,
                      self.rect.centery - t.get_height()//2))


class MainMenu:
    """
    Pantalla de bienvenida: selección de casino/preset de reglas.
    El nombre del jugador ya viene fijado por el perfil elegido en la
    pantalla anterior ("¿Quién juega?"), así que aquí solo se muestra
    como recordatorio. Devuelve preset_name cuando el jugador pulsa START.
    """

    # Entrada especial al final de la lista de presets: abre RulesEditor
    # en vez de arrancar la partida directamente.
    CUSTOM_LABEL = "Personalizado..."

    def __init__(self, screen: pygame.Surface, player_name: str = "Jugador",
                 seats: Optional[list[tuple[int, str]]] = None, sounds=None) -> None:
        self.screen = screen
        self.sw, self.sh = screen.get_size()
        self.player_name = player_name
        # Perfiles sentados a la mesa en esta sesión (1-3), para poder
        # abrir su historial de manos sin salir del menú. Puede venir
        # vacío/None (p. ej. tests que construyen MainMenu a mano).
        self._seats: list[tuple[int, str]] = seats or []
        # Instancia real de ui.sounds.SoundManager (Fase 16): se pasa a
        # SettingsScreen para que el volumen cambie al instante mientras
        # se arrastra el slider, no solo al volver al menú. None es
        # válido (p. ej. tests) -- SettingsScreen simplemente no podrá
        # dar preview en vivo, pero sigue aplicando y persistiendo bien.
        self._sounds = sounds
        self._done   = False
        self._result: Optional[str] = None
        # Reglas construidas a mano en RulesEditor, si el jugador elige y
        # confirma "Personalizado..." (None mientras no lo haya hecho).
        self._custom_rules: Optional[Rules] = None

        # Desafío elegido en ChallengeSelect (Fase 25), si el jugador entra
        # ahí y confirma uno -- en ese caso se cierra el menú al instante
        # (elegir el desafío YA es "empezar", no hace falta pulsar JUGAR
        # aparte). None mientras no se haya elegido ninguno.
        self._chosen_challenge: Optional[Challenge] = None

        # Fuentes
        self._font_title  = pygame.font.SysFont(None, 64, bold=True)
        self._font_sub    = pygame.font.SysFont(None, 28, bold=True)
        self._font_body   = pygame.font.SysFont(None, 22)
        self._font_small  = pygame.font.SysFont(None, 18)

        # Estado
        self._preset_idx  = 0
        self._preset_names = list(PRESETS.keys()) + [self.CUSTOM_LABEL]

        # Construir items de preset
        self._preset_items: list[MenuItem] = []
        self._build_preset_items()

        # Botón START
        self._start_rect = pygame.Rect(self.sw//2 - 120, self.sh - 90, 240, 52)
        self._start_hover = False

        # Botón "Historial" (esquina superior izquierda) -- abre el
        # historial de manos de quien está sentado a la mesa sin salir
        # del menú ni empezar a jugar.
        self._history_rect = pygame.Rect(20, 20, 150, 32)
        self._history_hover = False

        # Botón "Desafíos" (Fase 25), justo debajo de Historial -- solo
        # tiene sentido en solitario (los 4 desafíos del catálogo están
        # pensados para un jugador contra la casa, con sus propias fichas
        # iniciales y límite de manos), así que se oculta si hay más de
        # un asiento en la mesa.
        self._challenges_rect = pygame.Rect(20, 60, 150, 32)
        self._challenges_hover = False

        # Botón "Ajustes" (esquina superior derecha, simétrico al de
        # Historial) -- temas visuales y audio, aplicados/persistidos al
        # instante desde ui/settings_screen.py, sin salir del menú.
        self._settings_rect = pygame.Rect(self.sw - 170, 20, 150, 32)
        self._settings_hover = False

        # Botón "Conteo" (Fase 30), justo debajo de Ajustes -- simétrico a
        # "Desafíos" bajo Historial. Siempre visible (a diferencia de
        # Desafíos, no depende de cuántos jugadores haya sentados: es una
        # herramienta de entrenamiento personal, no una partida con
        # fichas ni resultado que dependa de con quién se juegue).
        self._counting_rect = pygame.Rect(self.sw - 170, 60, 150, 32)
        self._counting_hover = False

        # Animación de fondo
        self._anim_offset = 0.0

    # ------------------------------------------------------------------
    def _build_preset_items(self) -> None:
        """Coloca la lista de presets justo DEBAJO de la cabecera fija
        ("Jugador: X" / separador / "Selecciona el casino:") en vez de
        centrarla verticalmente en base a cuántos presets haya -- con el
        centrado antiguo, cada preset nuevo que se añadía al catálogo
        empujaba la lista entera hacia arriba, hasta llegar a solaparse
        con esa cabecera (se notó al añadir los presets de la Fase 23:
        con 9 entradas en vez de 6 el primer item ya invadía la cabecera).
        Los items también se hicieron algo más compactos (34px en vez de
        44px) para que quepan con holgura hasta el botón JUGAR."""
        self._preset_items.clear()
        item_w, item_h, gap = 320, 34, 6
        header_bottom = (self.sh // 2 - 148) + 46   # justo bajo "Selecciona el casino:"
        start_y = header_bottom
        x = self.sw // 2 - item_w // 2

        for i, name in enumerate(self._preset_names):
            y = start_y + i * (item_h + gap)
            display = i18n.t("menu.custom_option") if name == self.CUSTOM_LABEL else i18n.preset_label(name)
            item = MenuItem(
                text=display, value=name,
                x=x, y=y, w=item_w, h=item_h,
                font=self._font_body,
                selected=(i == self._preset_idx),
            )
            self._preset_items.append(item)

    # ------------------------------------------------------------------
    def run(self) -> tuple[str, Optional[Rules], Optional[Challenge]]:
        """Bucle bloqueante. Devuelve (preset_name, custom_rules, challenge).
        En el caso normal challenge es None; si el jugador eligió y
        confirmó un Desafío (Fase 25), preset_name/custom_rules no
        importan (se ignoran) y challenge trae el Challenge elegido. Si
        eligió y confirmó "Personalizado...", preset_name vale
        "Personalizado" y custom_rules trae el objeto Rules construido a
        mano en RulesEditor."""
        clock = pygame.time.Clock()
        while not self._done:
            dt = clock.tick(60)
            self._anim_offset += 0.3

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit
                self._handle_event(event)

            self._draw()
            pygame.display.flip()

        if self._chosen_challenge is not None:
            return "", None, self._chosen_challenge
        if self._custom_rules is not None:
            return "Personalizado", self._custom_rules, None
        return self._preset_names[self._preset_idx], None, None

    def _show_challenges(self) -> None:
        from ui.challenge_select import ChallengeSelect
        challenge = ChallengeSelect(self.screen).run()
        if challenge is not None:
            self._chosen_challenge = challenge
            self._done = True

    def _show_history(self) -> None:
        """Abre el historial de manos de los perfiles sentados en esta
        sesión (1 en solitario, hasta 3 en multijugador -- con pestañas
        para saltar entre ellos si hay más de uno). No hace nada si no
        hay perfiles (p. ej. un MainMenu construido a mano en un test)."""
        if not self._seats:
            return
        HandHistoryScreen(self.screen, self._seats, initial_index=0).run()

    def _show_settings(self) -> None:
        from ui.settings_screen import SettingsScreen  # import diferido: evita ciclos de import
        SettingsScreen(self.screen, sounds=self._sounds).run()
        # El idioma pudo cambiar en Ajustes (Fase 26): los MenuItem de
        # preset llevan su texto ya renderizado como string normal (no
        # se traducen en cada frame como el resto de la UI), así que hay
        # que reconstruirlos para que se vean en el idioma nuevo sin
        # tener que volver a abrir el menú desde cero.
        self._build_preset_items()

    def _show_counting(self) -> None:
        from ui.counting_trainer import CardCountingTrainer  # import diferido: evita ciclos de import
        CardCountingTrainer(self.screen).run()

    def _confirm_selection(self) -> None:
        """Se llama al pulsar Enter o el botón JUGAR. Si el preset
        seleccionado es "Personalizado...", abre RulesEditor en vez de
        arrancar ya la partida -- si se cancela (vuelve sin confirmar),
        el menú se queda tal cual, esperando otra selección."""
        if self._preset_names[self._preset_idx] == self.CUSTOM_LABEL:
            seed = self._custom_rules or vegas_strip()
            rules = RulesEditor(self.screen, seed).run()
            if rules is not None:
                self._custom_rules = rules
                self._done = True
        else:
            self._done = True

    # ------------------------------------------------------------------
    def _handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN:
            self._start_hover = self._start_rect.collidepoint(event.pos)
            if self._start_rect.collidepoint(event.pos):
                self._confirm_selection()
            elif self._seats and self._history_rect.collidepoint(event.pos):
                self._show_history()
            elif len(self._seats) <= 1 and self._challenges_rect.collidepoint(event.pos):
                self._show_challenges()
            elif self._settings_rect.collidepoint(event.pos):
                self._show_settings()
            elif self._counting_rect.collidepoint(event.pos):
                self._show_counting()

        if event.type == pygame.MOUSEMOTION:
            self._start_hover = self._start_rect.collidepoint(event.pos)
            self._history_hover = self._history_rect.collidepoint(event.pos)
            self._challenges_hover = self._challenges_rect.collidepoint(event.pos)
            self._settings_hover = self._settings_rect.collidepoint(event.pos)
            self._counting_hover = self._counting_rect.collidepoint(event.pos)

        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self._confirm_selection()
        if event.type == pygame.KEYDOWN and event.key == pygame.K_h:
            self._show_history()
        if event.type == pygame.KEYDOWN and event.key == pygame.K_c:
            self._show_counting()

        # Selección de preset con click o teclado
        for i, item in enumerate(self._preset_items):
            if item.handle_event(event):
                self._preset_idx = i
                for j, it in enumerate(self._preset_items):
                    it.selected = (j == i)

        # Flechas arriba/abajo
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self._preset_idx = max(0, self._preset_idx - 1)
                for j, it in enumerate(self._preset_items):
                    it.selected = (j == self._preset_idx)
            elif event.key == pygame.K_DOWN:
                self._preset_idx = min(len(self._preset_names)-1, self._preset_idx + 1)
                for j, it in enumerate(self._preset_items):
                    it.selected = (j == self._preset_idx)
            # (Enter ya se gestiona arriba, sin necesidad de comprobar
            # ningún campo de texto activo — este menú ya no tiene uno)

    # ------------------------------------------------------------------
    def _draw(self) -> None:
        surf = self.screen

        # Fondo degradado oscuro
        surf.fill(cfg.COLOR_BG)
        self._draw_bg_pattern(surf)

        # Título
        title = self._font_title.render("BLACKJACK PRO", True, cfg.COLOR_GOLD)
        shadow = self._font_title.render("BLACKJACK PRO", True, (0, 0, 0))
        tx = self.sw//2 - title.get_width()//2
        surf.blit(shadow, (tx+3, 43))
        surf.blit(title,  (tx,   40))

        sub = self._font_small.render("Casino Edition", True, (180, 160, 100))
        sub_x = self.sw//2 - sub.get_width()//2
        sub_y = 110
        surf.blit(sub, (sub_x, sub_y))
        star_cy = sub_y + sub.get_height() // 2
        icons.star(surf, sub_x - 16, star_cy, 7, (180, 160, 100))
        icons.star(surf, sub_x + sub.get_width() + 16, star_cy, 7, (180, 160, 100))

        # Recordatorio del perfil activo (el nombre ya se eligió en la
        # pantalla anterior — aquí solo se muestra, no se edita)
        greeting = self._font_sub.render(i18n.t("menu.player_label", name=self.player_name), True, cfg.COLOR_TEXT)
        surf.blit(greeting, (self.sw//2 - greeting.get_width()//2, self.sh//2 - 200))

        # Separador
        sep_y = self.sh//2 - 148
        pygame.draw.line(surf, (80, 80, 80), (self.sw//2 - 200, sep_y), (self.sw//2 + 200, sep_y), 1)

        # Subtítulo preset
        preset_lbl = self._font_sub.render(i18n.t("menu.select_casino"), True, cfg.COLOR_TEXT)
        surf.blit(preset_lbl, (self.sw//2 - preset_lbl.get_width()//2, sep_y + 8))

        # Items de preset
        for item in self._preset_items:
            item.draw(surf)

        # Info del preset seleccionado (o, si es "Personalizado...", un
        # resumen de las reglas ya ajustadas -- o una pista si aún no se
        # ha entrado nunca al editor)
        preset_name = self._preset_names[self._preset_idx]
        if preset_name == self.CUSTOM_LABEL:
            if self._custom_rules is not None:
                info_text = str(self._custom_rules)
            else:
                info_text = i18n.t("menu.custom_hint")
        else:
            info_text = str(get_preset(preset_name))
        info = self._font_small.render(info_text, True, (150, 150, 150))
        info_y = self._preset_items[-1].rect.bottom + 10
        surf.blit(info, (self.sw//2 - info.get_width()//2, info_y))

        # Botón START
        start_col = cfg.COLOR_GOLD if self._start_hover else (160, 130, 40)
        pygame.draw.rect(surf, (20, 15, 0), self._start_rect, border_radius=10)
        pygame.draw.rect(surf, start_col, self._start_rect, 2, border_radius=10)
        start_text = self._font_sub.render(i18n.t("menu.play_button"), True, start_col)
        icon_gap = 10
        total_w = start_text.get_width() + start_text.get_height() * 0.7 + icon_gap
        tx = self._start_rect.centerx - int(total_w) // 2
        ty = self._start_rect.centery - start_text.get_height() // 2
        icons.triangle_right(surf, tx, self._start_rect.centery, start_text.get_height() * 0.6, start_col)
        surf.blit(start_text, (tx + start_text.get_height() * 0.7 + icon_gap, ty))

        hint_text = i18n.t("menu.hint_base")
        if self._seats:
            hint_text += i18n.t("menu.hint_history_suffix")
        hint_text += i18n.t("menu.hint_counting_suffix")
        hint = self._font_small.render(hint_text, True, (80, 80, 80))
        surf.blit(hint, (self.sw//2 - hint.get_width()//2, self.sh - 28))

        # Versión (Fase 25) -- esquina inferior izquierda, discreta.
        ver = self._font_small.render(f"v{cfg.APP_VERSION}", True, (70, 70, 70))
        surf.blit(ver, (14, self.sh - ver.get_height() - 10))

        # Botón "Historial" -- solo tiene sentido si hay perfiles sentados
        # a la mesa (siempre los hay salvo en algún test manual).
        if self._seats:
            hist_col = cfg.COLOR_GOLD if self._history_hover else (140, 140, 140)
            pygame.draw.rect(surf, (20, 15, 0), self._history_rect, border_radius=8)
            pygame.draw.rect(surf, hist_col, self._history_rect, 1, border_radius=8)
            icons.list_icon(surf, self._history_rect.x + 20, self._history_rect.centery, 9, hist_col)
            hist_txt = self._font_small.render(i18n.t("menu.history_button"), True, hist_col)
            surf.blit(hist_txt, (self._history_rect.x + 36,
                                  self._history_rect.centery - hist_txt.get_height() // 2))

        # Botón "Desafíos" (Fase 25) -- solo en solitario (ver comentario
        # en __init__).
        if len(self._seats) <= 1:
            ch_col = cfg.COLOR_GOLD if self._challenges_hover else (140, 140, 140)
            pygame.draw.rect(surf, (20, 15, 0), self._challenges_rect, border_radius=8)
            pygame.draw.rect(surf, ch_col, self._challenges_rect, 1, border_radius=8)
            icons.star(surf, self._challenges_rect.x + 20, self._challenges_rect.centery, 9, ch_col)
            ch_txt = self._font_small.render(i18n.t("menu.challenges_button"), True, ch_col)
            surf.blit(ch_txt, (self._challenges_rect.x + 36,
                                self._challenges_rect.centery - ch_txt.get_height() // 2))

        # Botón "Ajustes" (temas visuales, audio) -- siempre visible.
        set_col = cfg.COLOR_GOLD if self._settings_hover else (140, 140, 140)
        pygame.draw.rect(surf, (20, 15, 0), self._settings_rect, border_radius=8)
        pygame.draw.rect(surf, set_col, self._settings_rect, 1, border_radius=8)
        icons.gear_icon(surf, self._settings_rect.x + 20, self._settings_rect.centery, 10, set_col)
        set_txt = self._font_small.render(i18n.t("menu.settings_button"), True, set_col)
        surf.blit(set_txt, (self._settings_rect.x + 36,
                             self._settings_rect.centery - set_txt.get_height() // 2))

        # Botón "Conteo" (Fase 30) -- siempre visible, simétrico a
        # Desafíos bajo Historial (ver comentario en __init__).
        cnt_col = cfg.COLOR_GOLD if self._counting_hover else (140, 140, 140)
        pygame.draw.rect(surf, (20, 15, 0), self._counting_rect, border_radius=8)
        pygame.draw.rect(surf, cnt_col, self._counting_rect, 1, border_radius=8)
        icons.draw_suit(surf, "S", self._counting_rect.x + 20, self._counting_rect.centery, 14, cnt_col)
        cnt_txt = self._font_small.render(i18n.t("menu.counting_button"), True, cnt_col)
        surf.blit(cnt_txt, (self._counting_rect.x + 36,
                             self._counting_rect.centery - cnt_txt.get_height() // 2))

    def _draw_bg_pattern(self, surf: pygame.Surface) -> None:
        """Patrón de rombos animado en el fondo."""
        import math
        col = (35, 100, 55, 18)
        pat = pygame.Surface((self.sw, self.sh), pygame.SRCALPHA)
        step = 60
        offset = int(self._anim_offset % step)
        for x in range(-step + offset, self.sw + step, step):
            for y in range(-step, self.sh + step, step):
                pts = [(x, y-step//2), (x+step//2, y), (x, y+step//2), (x-step//2, y)]
                pygame.draw.polygon(pat, col, pts, 1)
        surf.blit(pat, (0, 0))


class _RuleRow:
    """Una fila del editor de reglas: una etiqueta + un valor que se
    puede recorrer con flechas ◄ ► (clic o teclado), tomado de una lista
    fija de opciones válidas para ese campo -- así nunca se puede dejar
    una combinación de reglas inválida (p. ej. un número de mazos que el
    motor no sepa manejar)."""

    def __init__(self, attr: str, label: str, options: list, fmt: Callable,
                 x: int, y: int, w: int, h: int, font: pygame.font.Font) -> None:
        self.attr = attr
        self.label = label
        self.options = options
        self.fmt = fmt
        self.rect = pygame.Rect(x, y, w, h)
        self.font = font
        self.selected = False
        self.index = 0

    def set_value(self, value) -> None:
        try:
            self.index = self.options.index(value)
        except ValueError:
            self.index = 0

    @property
    def value(self):
        return self.options[self.index]

    def step(self, direction: int) -> None:
        self.index = (self.index + direction) % len(self.options)

    # Ancho reservado para el texto del valor, entre las dos flechas --
    # tiene que caber el valor más largo de cualquier fila ("Cualquier 2
    # cartas", "3 (hasta 4 manos)", etc.) sin pisar ni las flechas ni la
    # etiqueta de la izquierda.
    VALUE_ZONE_W = 150

    def arrow_rects(self) -> tuple[pygame.Rect, pygame.Rect]:
        size = self.rect.h - 14
        cy_top = self.rect.y + (self.rect.h - size) // 2
        pad_right = 10
        gap = 6
        right_rect = pygame.Rect(self.rect.right - pad_right - size, cy_top, size, size)
        left_rect = pygame.Rect(
            right_rect.x - gap - self.VALUE_ZONE_W - gap - size, cy_top, size, size)
        return left_rect, right_rect

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Devuelve True si el evento cambió el valor o seleccionó la fila."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            left_rect, right_rect = self.arrow_rects()
            if left_rect.collidepoint(event.pos):
                self.step(-1)
                return True
            if right_rect.collidepoint(event.pos):
                self.step(1)
                return True
            if self.rect.collidepoint(event.pos):
                return True  # solo selecciona la fila, sin cambiar valor
        return False

    def draw(self, surf: pygame.Surface) -> None:
        bg = (212, 175, 55, 30) if self.selected else (255, 255, 255, 8)
        border = cfg.COLOR_GOLD if self.selected else (90, 90, 90)
        box = pygame.Surface((self.rect.w, self.rect.h), pygame.SRCALPHA)
        pygame.draw.rect(box, bg, box.get_rect(), border_radius=6)
        pygame.draw.rect(box, border, box.get_rect(), 1, border_radius=6)
        surf.blit(box, (self.rect.x, self.rect.y))

        label_col = cfg.COLOR_TEXT if self.selected else (170, 170, 170)
        lbl = self.font.render(i18n.t(self.label), True, label_col)
        surf.blit(lbl, (self.rect.x + 10, self.rect.centery - lbl.get_height() // 2))

        left_rect, right_rect = self.arrow_rects()
        arrow_col = cfg.COLOR_GOLD if self.selected else (140, 140, 140)
        icons.triangle_left(surf, left_rect.right - 4, left_rect.centery, left_rect.h * 0.55, arrow_col)
        icons.triangle_right(surf, right_rect.x + 4, right_rect.centery, right_rect.h * 0.55, arrow_col)

        val_text = self.fmt(self.value)
        val = self.font.render(val_text, True, cfg.COLOR_GOLD if self.selected else (210, 210, 210))
        val_cx = (left_rect.right + right_rect.x) // 2
        surf.blit(val, (val_cx - val.get_width() // 2, self.rect.centery - val.get_height() // 2))


def _fmt_yn(v: bool) -> str:
    return i18n.t("menu.yes") if v else i18n.t("menu.no")


class RulesEditor:
    """Pantalla para ajustar a mano cada regla de core.rules.Rules, en vez
    de estar limitado a los presets de casino fijos. Se abre desde
    MainMenu al elegir "Personalizado..." y pulsar JUGAR. Bucle bloqueante
    que devuelve un objeto Rules al confirmar, o None si se cancela (ESC /
    botón Volver) -- en ese caso el menú anterior no cambia nada."""

    # NOTA (Fase 26): el segundo elemento de cada tupla es ahora una
    # CLAVE de i18n (no el texto ya en español) -- _RuleRow.draw() la
    # traduce en cada frame con i18n.t(), así que cambiar el idioma
    # desde Ajustes se refleja al instante sin reconstruir las filas.
    # Los `fmt` que antes devolvían texto en español fijo ahora llaman a
    # i18n.t() por el mismo motivo; los que solo formatean números/signos
    # ($, %, Sí/No genérico vía _fmt_yn) se dejan igual en los dos idiomas.
    FIELDS: list[tuple[str, str, list, Callable]] = [
        ("num_decks", "menu.field.num_decks", [1, 2, 4, 6, 8], lambda v: str(v)),
        ("penetration", "menu.field.penetration",
         [0.5, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85], lambda v: f"{v:.0%}"),
        ("dealer_rule", "menu.field.dealer_rule",
         [DealerRule.STAND_SOFT_17, DealerRule.HIT_SOFT_17],
         lambda v: i18n.t("menu.dealer_stand_s17") if v == DealerRule.STAND_SOFT_17 else i18n.t("menu.dealer_hit_h17")),
        ("blackjack_payout", "menu.field.blackjack_payout",
         [BlackjackPayout.THREE_TO_TWO, BlackjackPayout.SIX_TO_FIVE, BlackjackPayout.ONE_TO_ONE],
         lambda v: v.value),
        ("double_rule", "menu.field.double_rule",
         [DoubleRule.ANY_TWO, DoubleRule.NINE_TEN_ELEVEN],
         lambda v: i18n.t("menu.double_any_two") if v == DoubleRule.ANY_TWO else i18n.t("menu.double_9_10_11")),
        ("double_after_split", "menu.field.double_after_split", [True, False], lambda v: _fmt_yn(v)),
        ("max_splits", "menu.field.max_splits", [0, 1, 2, 3],
         lambda v: i18n.t("menu.max_splits_fmt", v=v, n=v + 1)),
        ("resplit_aces", "menu.field.resplit_aces", [True, False], lambda v: _fmt_yn(v)),
        ("hit_split_aces", "menu.field.hit_split_aces", [True, False], lambda v: _fmt_yn(v)),
        ("surrender_rule", "menu.field.surrender_rule",
         [SurrenderRule.NONE, SurrenderRule.LATE, SurrenderRule.EARLY],
         lambda v: {"none": i18n.t("menu.surrender_none"), "late": i18n.t("menu.surrender_late"),
                    "early": i18n.t("menu.surrender_early")}[v.value]),
        ("insurance_allowed", "menu.field.insurance_allowed", [True, False], lambda v: _fmt_yn(v)),
        ("even_money_allowed", "menu.field.even_money_allowed", [True, False], lambda v: _fmt_yn(v)),
        ("min_bet", "menu.field.min_bet", [5.0, 10.0, 25.0, 50.0], lambda v: f"${v:.0f}"),
        ("max_bet", "menu.field.max_bet",
         [100.0, 250.0, 500.0, 1000.0, 2000.0, 5000.0], lambda v: f"${v:.0f}"),
        ("starting_chips", "menu.field.starting_chips",
         [200.0, 500.0, 1000.0, 2000.0, 5000.0, 10000.0], lambda v: f"${v:.0f}"),
        ("five_card_charlie", "menu.field.five_card_charlie", [True, False], lambda v: _fmt_yn(v)),
        ("original_bets_only", "menu.field.original_bets_only", [True, False], lambda v: _fmt_yn(v)),
        ("perfect_pairs_allowed", "menu.field.perfect_pairs_allowed", [True, False], lambda v: _fmt_yn(v)),
        ("twentyone_plus_three_allowed", "menu.field.twentyone_plus_three_allowed", [True, False], lambda v: _fmt_yn(v)),
        ("side_bet_max", "menu.field.side_bet_max",
         [10.0, 25.0, 50.0, 100.0, 250.0, 500.0], lambda v: f"${v:.0f}"),
    ]

    def __init__(self, screen: pygame.Surface, seed: Optional[Rules] = None) -> None:
        self.screen = screen
        self.sw, self.sh = screen.get_size()
        self._done = False
        self._confirmed = False
        self._row_idx = 0

        self._font_title = pygame.font.SysFont(None, 40, bold=True)
        self._font_row   = pygame.font.SysFont(None, 20)
        self._font_small = pygame.font.SysFont(None, 18)

        seed = seed or vegas_strip()
        self._rows: list[_RuleRow] = []
        self._build_rows(seed)

        self._play_rect  = pygame.Rect(self.sw // 2 + 20, self.sh - 74, 200, 48)
        self._back_rect  = pygame.Rect(self.sw // 2 - 220, self.sh - 74, 200, 48)
        self._reset_rect = pygame.Rect(self.sw - 190, 20, 160, 30)
        self._play_hover = self._back_hover = self._reset_hover = False

    # ------------------------------------------------------------------
    def _build_rows(self, seed: Rules) -> None:
        self._rows.clear()
        cols, rows_per_col = 2, (len(self.FIELDS) + 1) // 2
        row_w, row_h, gap_x, gap_y = 470, 34, 40, 6
        total_w = cols * row_w + gap_x
        start_x = self.sw // 2 - total_w // 2
        start_y = 110

        for i, (attr, label, options, fmt) in enumerate(self.FIELDS):
            col, row = divmod(i, rows_per_col)
            x = start_x + col * (row_w + gap_x)
            y = start_y + row * (row_h + gap_y)
            item = _RuleRow(attr, label, options, fmt, x, y, row_w, row_h, self._font_row)
            item.set_value(getattr(seed, attr))
            self._rows.append(item)
        if self._rows:
            self._rows[0].selected = True

    def _select(self, idx: int) -> None:
        idx = max(0, min(len(self._rows) - 1, idx))
        for i, row in enumerate(self._rows):
            row.selected = (i == idx)
        self._row_idx = idx

    def _build_rules(self) -> Rules:
        kwargs = {row.attr: row.value for row in self._rows}
        return Rules(**kwargs)

    def _reset(self) -> None:
        seed = vegas_strip()
        for row in self._rows:
            row.set_value(getattr(seed, row.attr))

    # ------------------------------------------------------------------
    def run(self) -> Optional[Rules]:
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
        return self._build_rules() if self._confirmed else None

    def _handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._done = True
                self._confirmed = False
            elif event.key == pygame.K_RETURN:
                self._done = True
                self._confirmed = True
            elif event.key == pygame.K_UP:
                self._select(self._row_idx - 1)
            elif event.key == pygame.K_DOWN:
                self._select(self._row_idx + 1)
            elif event.key == pygame.K_LEFT:
                self._rows[self._row_idx].step(-1)
            elif event.key == pygame.K_RIGHT:
                self._rows[self._row_idx].step(1)

        if event.type == pygame.MOUSEMOTION:
            self._play_hover = self._play_rect.collidepoint(event.pos)
            self._back_hover = self._back_rect.collidepoint(event.pos)
            self._reset_hover = self._reset_rect.collidepoint(event.pos)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._play_rect.collidepoint(event.pos):
                self._done = True
                self._confirmed = True
                return
            if self._back_rect.collidepoint(event.pos):
                self._done = True
                self._confirmed = False
                return
            if self._reset_rect.collidepoint(event.pos):
                self._reset()
                return
            for i, row in enumerate(self._rows):
                if row.handle_event(event):
                    self._select(i)

    # ------------------------------------------------------------------
    def _draw(self) -> None:
        surf = self.screen
        surf.fill(cfg.COLOR_BG)

        title = self._font_title.render(i18n.t("menu.rules_editor_title"), True, cfg.COLOR_GOLD)
        surf.blit(title, (self.sw // 2 - title.get_width() // 2, 30))

        # Botón "Restablecer" (esquina superior derecha)
        reset_col = cfg.COLOR_GOLD if self._reset_hover else (140, 140, 140)
        pygame.draw.rect(surf, (20, 15, 0), self._reset_rect, border_radius=8)
        pygame.draw.rect(surf, reset_col, self._reset_rect, 1, border_radius=8)
        icons.refresh_arrow(surf, self._reset_rect.x + 20, self._reset_rect.centery, 8, reset_col)
        reset_txt = self._font_small.render(i18n.t("menu.reset_button"), True, reset_col)
        surf.blit(reset_txt, (self._reset_rect.x + 36, self._reset_rect.centery - reset_txt.get_height() // 2))

        for row in self._rows:
            row.draw(surf)

        hint = self._font_small.render(i18n.t("menu.rules_hint"), True, (110, 110, 110))
        surf.blit(hint, (self.sw // 2 - hint.get_width() // 2, self.sh - 108))

        # Botones Volver / JUGAR
        back_col = cfg.COLOR_TEXT if self._back_hover else (150, 150, 150)
        pygame.draw.rect(surf, (20, 15, 0), self._back_rect, border_radius=10)
        pygame.draw.rect(surf, back_col, self._back_rect, 2, border_radius=10)
        back_txt = self._font_row.render(i18n.t("menu.back_button"), True, back_col)
        surf.blit(back_txt, (self._back_rect.centerx - back_txt.get_width() // 2,
                              self._back_rect.centery - back_txt.get_height() // 2))

        play_col = cfg.COLOR_GOLD if self._play_hover else (160, 130, 40)
        pygame.draw.rect(surf, (20, 15, 0), self._play_rect, border_radius=10)
        pygame.draw.rect(surf, play_col, self._play_rect, 2, border_radius=10)
        play_txt = self._font_row.render(i18n.t("menu.play_button"), True, play_col)
        icon_gap = 8
        total_w = play_txt.get_width() + play_txt.get_height() * 0.7 + icon_gap
        tx = self._play_rect.centerx - int(total_w) // 2
        ty = self._play_rect.centery - play_txt.get_height() // 2
        icons.triangle_right(surf, tx, self._play_rect.centery, play_txt.get_height() * 0.6, play_col)
        surf.blit(play_txt, (tx + play_txt.get_height() * 0.7 + icon_gap, ty))