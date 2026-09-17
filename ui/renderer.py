# ui/renderer.py
# Bucle principal Pygame: ventana, game loop, eventos y render completo.
# Conecta GameEngine ↔ Table ↔ CardSprites ↔ Buttons ↔ HUD ↔ Animations.
#
# Soporta 1-3 jugadores humanos en la misma mesa (multijugador local,
# "pasa y juega"): el área de cartas central siempre muestra al jugador
# que tiene el foco en cada momento (apostando, recibiendo cartas o
# jugando su turno) — igual que una mesa real, donde cada uno juega su
# mano cuando le toca — y una tira de asientos en la parte superior
# resume a todos los jugadores (avatar, fichas, estado). En solitario esa
# tira ni se dibuja, así que la partida de siempre se ve exactamente igual.
# -------------------------------------------------------------
from __future__ import annotations

import math
import random
import sys
import pygame
from typing import Optional

from config import settings as cfg
from config import i18n
from config.rules_presets import get_preset
from core.rules import Rules

from engine.game_engine import GameEngine
from engine.game_state import GameState, ActionResult, RoundResult
from engine.payout import HandPayout
from engine.challenges import Challenge

from ai.card_counter import HiLoCounter
from ai.basic_strategy import recommended_play

from ui.card_generator import CardGenerator
from ui.card_sprite import CardSprite
from ui.table import Table
from ui.buttons import ButtonBar, InsuranceBar
from ui.chip_stack import ChipTray
from ui.side_bets_ui import SideBetPanel
from ui.hud import HUD
from ui.animations import ParticleSystem, GlowEffect, ShuffleEffect, AchievementToast
from ui.menu import MainMenu
from ui.profile_select import ProfileSelect, SeatConfirmScreen, draw_avatar
from ui.sounds import SoundManager
from ui import icons


# ── Colores de resultado ──────────────────────────────────────────────
RESULT_COLORS = {
    RoundResult.WIN:          cfg.COLOR_WIN,
    RoundResult.BLACKJACK_WIN: cfg.COLOR_BJ,
    RoundResult.DEALER_BUST:  cfg.COLOR_WIN,
    RoundResult.LOSS:         cfg.COLOR_LOSE,
    RoundResult.PUSH:         cfg.COLOR_PUSH,
    RoundResult.SURRENDER:    cfg.COLOR_PUSH,
}
_RESULT_LABEL_KEYS = {
    RoundResult.WIN:           "renderer.result_win",
    RoundResult.BLACKJACK_WIN: "renderer.result_blackjack",
    RoundResult.DEALER_BUST:   "renderer.result_dealer_bust",
    RoundResult.LOSS:          "renderer.result_loss",
    RoundResult.PUSH:          "renderer.result_push",
    RoundResult.SURRENDER:     "renderer.result_surrender",
}


def _result_label(result) -> str:
    """Traducción en vivo del resultado de una mano (Fase 26) -- antes
    era un dict estático RESULT_LABELS construido una vez al importar el
    módulo; ahora se resuelve en cada llamada para reflejar el idioma
    activo en ese momento."""
    key = _RESULT_LABEL_KEYS.get(result)
    return i18n.t(key) if key else result.name


class Renderer:
    """
    Clase principal que gestiona la ventana Pygame y el bucle de juego.

    Uso:
        renderer = Renderer()
        renderer.run()
    """

    # ── Estados internos del renderer (distintos a GameState) ────────
    _MENU      = "menu"
    _BETTING   = "betting"
    _DEALING   = "dealing"    # reparto inicial en curso (multijugador: uno a uno)
    _PLAYING   = "playing"
    _INSURANCE = "insurance"
    _DEALER    = "dealer"     # turno automático del crupier (animado, sin botones)
    _RESULT    = "result"
    _GAMEOVER  = "gameover"
    _CHALLENGE_END = "challenge_end"   # Fase 25: fin de un Desafío (ganado o perdido)

    def __init__(self) -> None:
        # El mixer debe inicializarse con un formato conocido ANTES de
        # pygame.init() para que los SFX sintetizados (16-bit estéreo) casen.
        try:
            pygame.mixer.pre_init(44100, -16, 2, 512)
        except Exception:
            pass
        pygame.init()
        pygame.display.set_caption(cfg.WINDOW_TITLE)

        flags = pygame.FULLSCREEN if cfg.FULLSCREEN else 0
        self.screen = pygame.display.set_mode(
            (cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT), flags
        )
        self.clock = pygame.time.Clock()
        self.sw, self.sh = cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT

        # Superficie de escena: se dibuja aquí y se compone sobre self.screen
        # al final de cada frame, para poder aplicarle shake/zoom de cámara.
        self._scene_surf = pygame.Surface((self.sw, self.sh))

        # Tema visual guardado (Fase 15): se aplica ANTES de construir
        # Table/CardGenerator para que la primera partida ya salga con el
        # tema elegido la última vez, sin esperar a pasar por Ajustes.
        from engine.app_settings import get_settings
        app_settings = get_settings()
        cfg.apply_table_theme(app_settings.get("table_theme", cfg.DEFAULT_TABLE_THEME))
        cfg.apply_card_back_theme(app_settings.get("card_back_theme", cfg.DEFAULT_CARD_BACK_THEME))

        # Idioma guardado (Fase 26): igual que el tema, se aplica ANTES de
        # construir cualquier pantalla para que todo salga ya en el idioma
        # elegido la última vez, sin esperar a pasar por Ajustes.
        saved_language = app_settings.get("language")
        if saved_language:
            cfg.LANGUAGE = saved_language

        # Subsistemas de UI
        self.table      = Table(self.sw, self.sh)
        self.card_gen   = CardGenerator()
        self.hud        = HUD(self.sw, self.sh)
        self.particles  = ParticleSystem()
        self.counter    = HiLoCounter()
        self.sounds     = SoundManager()

        # Volumen/activación guardados (Fase 16): se aplican como ganancia
        # en caliente sobre la librería de sonido ya construida -- ver
        # SoundManager.set_*_volume/set_*_enabled. None significa "nunca
        # se tocó desde Ajustes", así que se respeta el comportamiento de
        # siempre (música sonando desde el menú, sin más).
        music_vol = app_settings.get("music_volume")
        sfx_vol = app_settings.get("sfx_volume")
        music_en = app_settings.get("music_enabled")
        sfx_en = app_settings.get("sfx_enabled")
        if sfx_vol is not None:
            self.sounds.set_sfx_volume(sfx_vol)
        if sfx_en is not None:
            self.sounds.set_sfx_enabled(sfx_en)
        if music_vol is not None:
            self.sounds.set_music_volume(music_vol)
        if music_en is not None:
            self.sounds.set_music_enabled(music_en)   # ya arranca/para la música según corresponda
        else:
            self.sounds.start_music()   # ambiente de fondo en bucle, ya desde el menú (comportamiento de siempre)

        # Estado del renderer
        self._state   = self._MENU
        self._engine: Optional[GameEngine] = None

        # Fase 25: Desafío activo (None en una partida normal) y su
        # resultado en cuanto se decide ("won"/"lost") -- ver _start_game,
        # _on_round_end, _on_state_change y _advance_from_result.
        self._challenge: Optional[Challenge] = None
        self._challenge_result: Optional[str] = None

        # Secuenciador del turno del crupier (revela y pide carta a carta,
        # esperando a que cada animación termine antes de seguir)
        self._dealer_seq_active = False
        self._dealer_seq_wait   = 0

        # Secuenciador del reparto inicial multijugador: pacea el paso de
        # un jugador al siguiente (ver _update_deal_sequence).
        self._deal_seq_wait = 0

        # Pausa multijugador: cuántos frames quedan mostrando la mano de
        # un jugador con el foco antes de pasar sola al siguiente — ver
        # _on_state_change/_update. `_turn_reveal_reason` distingue el
        # motivo ("blackjack": mano sin ninguna acción posible desde el
        # reparto; "double": se acaba de doblar y recibir la carta) para
        # que _seat_status_text muestre el texto adecuado en cada caso.
        self._turn_reveal_wait = 0
        self._turn_reveal_reason: Optional[str] = None

        # Cámara: shake (bust) y zoom/flash dorado (blackjack)
        self._shake_time  = 0
        self._shake_mag    = 0.0
        self._zoom_time    = 0
        self._zoom_total   = 0

        # Sprites de cartas activos
        self._dealer_sprites: list[CardSprite] = []
        self._player_sprites: list[list[CardSprite]] = []  # [hand_idx][card_idx]

        # Animaciones de barajado del zapato (ver _on_engine_message)
        self._shuffle_fx: list[ShuffleEffect] = []

        # Jugadores de esta sesión (1-3). seat_names/seat_avatars son
        # listas en el mismo orden que engine.players, para la tira de
        # asientos y los rótulos multijugador.
        self._seat_names: list[str] = []
        self._seat_avatars: list[tuple[str, tuple]] = []
        # A quién se está mostrando ahora mismo en la zona de cartas
        # central (None hasta que arranca la primera ronda).
        self._spotlight_player: Optional[int] = None

        # Logros: cola de avisos pendientes (uno detrás de otro) + qué
        # logros tiene desbloqueados CADA jugador (una lista de sets, en
        # el mismo orden que engine.players), para el panel F4.
        self._achievement_queue: list[tuple[int, object]] = []   # (player_index, achievement)
        self._active_toast: Optional[AchievementToast] = None
        self._unlocked_achievement_ids: list[set] = []

        # Apuesta en curso (fase betting) y última apuesta de cada jugador
        # (para el botón "Repetir"), por índice de jugador.
        self._pending_bet: float = 0.0
        self._last_bet_by_player: dict[int, float] = {}

        # Resultado pendiente de mostrar (formato plano, compat) y su
        # desglose por jugador (multijugador).
        self._payouts: list[HandPayout] = []
        self._payouts_by_player: list[list[HandPayout]] = []
        self._result_timer: int = 0
        self._result_glows: list[GlowEffect] = []

        # Botones (se crean tras conocer engine)
        self._btn_bar:       Optional[ButtonBar]    = None
        self._ins_bar:       Optional[InsuranceBar] = None
        self._chip_tray:     Optional[ChipTray]     = None
        self._side_bet_panel: Optional[SideBetPanel] = None
        self._deal_btn:      Optional[pygame.Rect]  = None
        self._deal_hover:    bool = False
        self._rebet_btn:     Optional[pygame.Rect]  = None
        self._rebet_hover:   bool = False

        # Fuentes auxiliares
        self._font_msg   = pygame.font.SysFont(None, 32, bold=True)
        self._font_small = pygame.font.SysFont(None, 20)
        self._font_big   = pygame.font.SysFont(None, 60, bold=True)
        self._font_seat  = pygame.font.SysFont(None, 18, bold=True)
        self._font_seat_small = pygame.font.SysFont(None, 15)

    # ──────────────────────────────────────────────────────────────────
    # Punto de entrada
    # ──────────────────────────────────────────────────────────────────
    def run(self) -> None:
        """Bucle principal. Bloquea hasta que el usuario cierra la ventana."""
        while True:
            self.clock.tick(cfg.FPS)

            if self._state == self._MENU:
                self._run_menu()
            else:
                self._handle_events()
                self._update()
                self._draw()
                pygame.display.flip()

    # ──────────────────────────────────────────────────────────────────
    # Menú principal — selección de jugadores ("lobby") + preset
    # ──────────────────────────────────────────────────────────────────
    def _run_menu(self) -> None:
        """Elige de 1 a 3 perfiles locales para esta sesión: siempre se
        pide al menos uno (como siempre), y tras cada uno se pregunta si
        se añade otro jugador (hasta 3) o se empieza ya a jugar — así el
        camino de "un solo jugador" sigue siendo tan directo como antes
        (una pantalla de perfil + Enter en la de confirmación)."""
        seats: list[tuple[int, str]] = []
        while True:
            exclude = {pid for pid, _ in seats}
            title = i18n.t("profile.title_default") if not seats else i18n.t("renderer.title_add_seat")
            profile_select = ProfileSelect(self.screen, exclude_ids=exclude, title=title)
            pid, name = profile_select.run()
            seats.append((pid, name))

            if len(seats) >= SeatConfirmScreen.MAX_SEATS:
                break
            again = SeatConfirmScreen(self.screen, seats).run()
            if not again:
                break

        greeting = seats[0][1] if len(seats) == 1 else ", ".join(n for _, n in seats)
        menu = MainMenu(self.screen, greeting, seats=seats, sounds=self.sounds)
        preset_name, custom_rules, challenge = menu.run()

        # El menú (o su pantalla de Ajustes, Fase 15) puede haber cambiado
        # el tema de mesa/cartas en caliente -- se invalida aquí, siempre,
        # sea o no que haya cambiado nada: reconstruir el fondo cacheado
        # de la mesa y el reverso cacheado de las cartas es barato y solo
        # ocurre al empezar una partida nueva, nunca por frame.
        self.table.invalidate()
        self.card_gen.invalidate_back()

        self._start_game(seats, preset_name, custom_rules, challenge)

    def _start_game(self, seats: list[tuple[int, str]], preset_name: str,
                     custom_rules: Optional[Rules] = None,
                     challenge: Optional[Challenge] = None) -> None:
        # Fase 25: un Desafío trae sus propias reglas/fichas (ver
        # Challenge.build_rules) y anula tanto preset_name como
        # custom_rules -- se etiqueta el hand_history con su nombre para
        # poder distinguirlo de una partida normal si se mira el
        # historial más tarde.
        self._challenge = challenge
        self._challenge_result: Optional[str] = None
        if challenge is not None:
            rules = challenge.build_rules()
            challenge_name, _ = i18n.challenge_text(challenge)
            preset_name = i18n.t("renderer.challenge_preset_label", name=challenge_name)
        else:
            # "Personalizado" trae ya el objeto Rules hecho a mano en
            # RulesEditor; cualquier otro nombre es uno de los presets
            # fijos de config/rules_presets.py, como siempre.
            rules = custom_rules if custom_rules is not None else get_preset(preset_name)
        players_cfg = [{"name": name, "profile_id": pid} for pid, name in seats]
        self._engine = GameEngine(rules=rules, players=players_cfg, preset_name=preset_name)
        self._engine.auto_dealer_turn = False   # la UI Pygame pacea el turno del crupier
        self._engine.auto_advance     = False   # y también el reparto inicial, jugador a jugador
        self.counter  = HiLoCounter()
        self.counter._decks_estimate = float(rules.num_decks)

        # Registrar callbacks del engine
        self._engine.on("on_card_dealt",   self._on_card_dealt)
        self._engine.on("on_state_change", self._on_state_change)
        self._engine.on("on_turn_change",  self._on_turn_change)
        self._engine.on("on_round_end",    self._on_round_end)
        self._engine.on("on_round_end_players", self._on_round_end_players)
        self._engine.on("on_action_result",self._on_action_result)
        self._engine.on("on_message",      self._on_engine_message)
        self._engine.on("on_achievements_unlocked", self._on_achievements_unlocked)
        self._engine.on("on_side_bets_result", self._on_side_bets_result)

        # Nombres/avatares de los asientos, para la tira multijugador
        self._seat_names = [name for _, name in seats]
        from engine.profile_store import get_store
        store = get_store()
        self._seat_avatars = []
        self._unlocked_achievement_ids = []
        for pid, _ in seats:
            data = store.get_profile(pid) if pid is not None else None
            if data:
                try:
                    color = tuple(int(c) for c in data["avatar_color"].split(","))
                except Exception:
                    color = (212, 175, 55)
                self._seat_avatars.append((data.get("avatar_shape", "S"), color))
            else:
                self._seat_avatars.append(("S", (212, 175, 55)))
            ids = store.get_unlocked_achievement_ids(pid) if pid is not None else set()
            self._unlocked_achievement_ids.append(ids)

        # Cola de avisos de logros pendientes: se reinicia con cada partida
        # nueva (los ya desbloqueados se cargan arriba, para el panel F4).
        self._achievement_queue = []
        self._active_toast = None
        self._spotlight_player = None

        # Construir controles
        self._btn_bar   = ButtonBar(self.sw, self.sh, self._on_player_action)
        self._chip_tray = ChipTray(self.sw, self.sh, self._on_chip_click)
        self._chip_tray.set_remove_callback(self._on_chip_undo)
        self._side_bet_panel = SideBetPanel(
            self.sw, self.sh,
            perfect_pairs_allowed=rules.perfect_pairs_allowed,
            twentyone_plus_three_allowed=rules.twentyone_plus_three_allowed,
        )
        self._deal_btn  = pygame.Rect(self.sw//2 - 80, self.sh - 70, 160, 44)
        self._rebet_btn = pygame.Rect(self.sw//2 + 90, self.sh - 70, 140, 44)

        self._dealer_sprites  = []
        self._player_sprites  = []
        self._pending_bet     = 0.0
        self._last_bet_by_player = {}
        self._training_correct = 0
        self._training_total   = 0
        self._training_feedback: Optional[tuple] = None   # (text, color, frames_left)

        self._engine.start_game()
        self._state = self._BETTING

    # ──────────────────────────────────────────────────────────────────
    # Eventos
    # ──────────────────────────────────────────────────────────────────
    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                self._handle_key(event)

            # Botones de acción (turno jugador)
            if self._state == self._PLAYING and self._btn_bar:
                self._btn_bar.handle_event(event)

            # Fichas (fase apuesta)
            if self._state == self._BETTING and self._chip_tray:
                self._chip_tray.handle_event(event)

            # Apuestas laterales (fase apuesta)
            if self._state == self._BETTING and self._side_bet_panel:
                self._side_bet_panel.handle_event(event)

            # Seguro
            if self._state == self._INSURANCE and self._ins_bar:
                self._ins_bar.handle_event(event)

            # Botón DEAL / REBET
            if event.type == pygame.MOUSEMOTION:
                if self._deal_btn:
                    self._deal_hover  = self._deal_btn.collidepoint(event.pos)
                if self._rebet_btn:
                    self._rebet_hover = self._rebet_btn.collidepoint(event.pos)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self._state == self._BETTING:
                    if self._deal_btn and self._deal_btn.collidepoint(event.pos):
                        self._confirm_bet()
                    if self._rebet_btn and self._rebet_btn.collidepoint(event.pos):
                        self._rebet()

            # Avanzar resultado con click o Enter
            if self._state == self._RESULT:
                if event.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
                    self._advance_from_result()

    def _handle_key(self, event: pygame.event.Event) -> None:
        key = event.key

        # Teclas globales
        if key == pygame.K_ESCAPE:
            self._state = self._MENU
            return
        if key == pygame.K_F1:
            cfg.SHOW_HINTS = not cfg.SHOW_HINTS
        if key == pygame.K_F2:
            cfg.SHOW_CARD_COUNTER = not cfg.SHOW_CARD_COUNTER
        if key == pygame.K_F3:
            self.hud.toggle_stats()
        if key == pygame.K_F4:
            self.hud.toggle_achievements()
        if key == pygame.K_F5:
            cfg.TRAINING_MODE = not cfg.TRAINING_MODE
            state = i18n.t("renderer.training_on") if cfg.TRAINING_MODE else i18n.t("renderer.training_off")
            self.hud.add_message(i18n.t("renderer.training_mode_toggle", state=state),
                                  self.sw // 2, self.sh // 2 - 60, cfg.COLOR_GOLD)
        if key == pygame.K_m:
            self.sounds.toggle_music()

        # Fase apuesta: Enter confirma
        if self._state == self._BETTING and key == pygame.K_RETURN:
            self._confirm_bet()

        # Seguro: Y / N
        if self._state == self._INSURANCE:
            if key == pygame.K_y:
                self._engine.accept_insurance(True)
            elif key == pygame.K_n:
                self._engine.accept_insurance(False)

    # ──────────────────────────────────────────────────────────────────
    # Lógica de apuesta
    # ──────────────────────────────────────────────────────────────────
    def _on_chip_click(self, amount: int) -> None:
        """Añade una ficha a la apuesta pendiente."""
        rules = self._engine.rules
        new_bet = self._pending_bet + amount
        if new_bet > rules.max_bet:
            return
        if new_bet > self._engine.player.chips:
            return
        self._pending_bet = new_bet
        if self._chip_tray:
            self._chip_tray.push_chip(amount)
        self.sounds.play("chip")

    def _on_chip_undo(self) -> None:
        """Click derecho en la mesa de apuesta: devuelve la última ficha."""
        if not self._chip_tray:
            return
        value = self._chip_tray.pop_chip()
        if value is not None:
            self._pending_bet = max(0.0, self._pending_bet - value)
            self.sounds.play("chip_undo")

    def _confirm_bet(self) -> None:
        if self._pending_bet < self._engine.rules.min_bet:
            self.hud.add_message(
                i18n.t("renderer.min_bet_warning", amount=int(self._engine.rules.min_bet)),
                self.sw//2, self.sh//2,
                cfg.COLOR_LOSE,
            )
            return
        bettor = self._engine.active_player_index
        self._last_bet_by_player[bettor] = self._pending_bet
        pp = self._side_bet_panel.value_for("perfect_pairs") if self._side_bet_panel else 0.0
        tp3 = self._side_bet_panel.value_for("21+3") if self._side_bet_panel else 0.0
        ok = self._engine.place_bet(self._pending_bet, perfect_pairs=pp, twentyone_plus_three=tp3)
        if ok:
            self._pending_bet = 0.0
            if self._side_bet_panel:
                self._side_bet_panel.reset()
            self.sounds.play("button")

    def _rebet(self) -> None:
        """Repite la última apuesta de quien tiene el turno de apostar."""
        bettor = self._engine.active_player_index
        last = self._last_bet_by_player.get(bettor, 0.0)
        if last >= self._engine.rules.min_bet:
            self._pending_bet = min(last, self._engine.player.chips)
            self._confirm_bet()

    # ──────────────────────────────────────────────────────────────────
    # Callbacks del engine
    # ──────────────────────────────────────────────────────────────────
    def _on_card_dealt(self, card, target: str, hand_index: int,
                        player_index: Optional[int] = None) -> None:
        """Crea un CardSprite animado al repartir.

        En multijugador, la zona central de cartas solo muestra al jugador
        que tiene el foco ahora mismo (ver _on_turn_change): las cartas de
        los demás se reparten igualmente en el motor, pero no se animan
        aquí hasta que les vuelve a tocar el turno (entonces se
        reconstruyen al instante, sin volar — ver _rebuild_spotlight_sprites)."""
        if target == "dealer":
            card_idx = len(self._dealer_sprites)
            tx = self.table.get_dealer_card_x(card_idx, card_idx + 1)
            rot, dy = self.table.get_dealer_card_fan(card_idx, card_idx + 1)
            ty = self.table.get_dealer_card_y() + dy
            sprite = CardSprite(
                card, self.card_gen,
                target_x=tx, target_y=ty,
                start_x=self.sw//2, start_y=-cfg.CARD_HEIGHT,
                delay=card_idx * 4 + random.randint(0, 2),
                fan_rotation=rot,
            )
            self._dealer_sprites.append(sprite)
            # Reposicionar cartas anteriores
            self._reposition_dealer_sprites()
            self.sounds.play("deal")

        else:  # player
            if player_index is not None and player_index != self._engine.active_player_index:
                # No es el jugador que tiene el foco ahora mismo: se repartió
                # de verdad en el motor, pero no se muestra hasta su turno.
                if card.face_up:
                    self.counter.register_card(card)
                self.counter.update_deck_estimate(self._engine.deck)
                return

            # Asegurar que existe la lista para esta mano
            while len(self._player_sprites) <= hand_index:
                self._player_sprites.append([])

            card_idx = len(self._player_sprites[hand_index])
            num_hands = len(self._engine.player.hands)
            tx = self.table.get_player_card_x(card_idx, card_idx + 1,
                                               hand_index, num_hands)
            rot, dy = self.table.get_player_card_fan(card_idx, card_idx + 1)
            ty = self.table.get_player_card_y() + dy
            sprite = CardSprite(
                card, self.card_gen,
                target_x=tx, target_y=ty,
                start_x=self.sw//2, start_y=self.sh + cfg.CARD_HEIGHT,
                delay=card_idx * 4 + random.randint(0, 2),
                fan_rotation=rot,
            )
            self._player_sprites[hand_index].append(sprite)
            self._reposition_player_sprites()
            self.sounds.play("deal")

        # Registrar en contador (solo cartas visibles)
        if card.face_up:
            self.counter.register_card(card)
        self.counter.update_deck_estimate(self._engine.deck)

    def _reposition_dealer_sprites(self) -> None:
        total = len(self._dealer_sprites)
        for i, sprite in enumerate(self._dealer_sprites):
            nx = self.table.get_dealer_card_x(i, total)
            rot, dy = self.table.get_dealer_card_fan(i, total)
            ny = self.table.get_dealer_card_y() + dy
            sprite.set_fan_rotation(rot)
            if abs(sprite.target_x - nx) > 2 or abs(sprite.target_y - ny) > 2:
                sprite.move_to(nx, ny, fan_rotation=rot)

    def _reposition_player_sprites(self) -> None:
        num_hands = len(self._player_sprites)
        for hi, hand_sprites in enumerate(self._player_sprites):
            total = len(hand_sprites)
            for ci, sprite in enumerate(hand_sprites):
                nx = self.table.get_player_card_x(ci, total, hi, num_hands)
                rot, dy = self.table.get_player_card_fan(ci, total)
                ny = self.table.get_player_card_y() + dy
                sprite.set_fan_rotation(rot)
                if abs(sprite.target_x - nx) > 2 or abs(sprite.target_y - ny) > 2:
                    sprite.move_to(nx, ny, fan_rotation=rot)

    def _on_turn_change(self, player_index: int, phase: str) -> None:
        """El foco de la mesa pasa a `player_index` (fase 'bet' | 'deal' |
        'insurance' | 'play'). Si es un jugador distinto al que se estaba
        mostrando, la zona central de cartas se limpia; si además no
        estamos empezando a repartirle de cero ('deal'), sus cartas ya
        existentes se reconstruyen al instante (sin volar) — por ejemplo
        al volver a su turno de juego tras haber repartido a todos."""
        if player_index != self._spotlight_player:
            self._spotlight_player = player_index
            self._player_sprites = []
            if phase != "deal" and self._engine:
                self._rebuild_spotlight_sprites(player_index)

    def _rebuild_spotlight_sprites(self, player_index: int) -> None:
        """Reconstruye instantáneamente (sin animación de reparto) los
        sprites de las cartas que ya se le repartieron a este jugador."""
        player = self._engine.players[player_index]
        sprites: list[list[CardSprite]] = []
        for hi, hand in enumerate(player.hands):
            hand_sprites = []
            for ci, card in enumerate(hand.cards):
                tx = self.table.get_player_card_x(ci, len(hand.cards), hi, len(player.hands))
                rot, dy = self.table.get_player_card_fan(ci, len(hand.cards))
                ty = self.table.get_player_card_y() + dy
                sprite = CardSprite(card, self.card_gen, target_x=tx, target_y=ty,
                                     fan_rotation=rot)
                hand_sprites.append(sprite)
            sprites.append(hand_sprites)
        self._player_sprites = sprites

    def _on_state_change(self, new_state: GameState) -> None:
        match new_state:
            case GameState.BETTING:
                # El motor pasa a BETTING de forma síncrona nada más cerrar
                # la ronda (para quedar listo para la siguiente apuesta) o
                # al pasarle el turno de apostar al siguiente jugador, pero
                # si la UI está mostrando la pantalla de resultado no debe
                # cortarla de golpe: la limpieza (cartas, fichas, contador)
                # se pospone hasta que el propio renderer decida salir de
                # RESULT (ver _advance_from_result).
                if self._state == self._RESULT:
                    pass
                else:
                    self._apply_betting_reset()

            case GameState.DEALING:
                self._state = self._DEALING

            case GameState.PLAYER_TURN:
                self._state = self._PLAYING
                actions = self._engine.get_available_actions()
                if self._btn_bar:
                    self._btn_bar.set_available(actions)
                if not actions and len(self._engine.players) > 1:
                    # En multijugador, el foco puede caer en un jugador
                    # sin ninguna acción posible (Blackjack natural): se
                    # le enseña la mano un instante (ver _update) y se
                    # avanza sola, sin esperar ningún clic.
                    self._turn_reveal_wait = self._dealer_pause()
                    self._turn_reveal_reason = "blackjack"
                    self._player_message(
                        i18n.t("renderer.natural_blackjack", name=self._engine.player.name), cfg.COLOR_BJ)
                else:
                    self._turn_reveal_wait = 0
                    self._turn_reveal_reason = None

            case GameState.INSURANCE:
                self._state = self._INSURANCE
                hand = self._engine.player.active_hand
                is_em = (hand and hand.is_blackjack and
                         self._engine.rules.even_money_allowed)
                self._ins_bar = InsuranceBar(
                    self.sw, self.sh,
                    callback=self._on_insurance_answer,
                    is_even_money=bool(is_em),
                )

            case GameState.DEALER_TURN:
                # Turno automático del crupier: oculta los botones y arranca
                # el secuenciador que revela la hole card y pide carta a
                # carta, pausando a que cada animación termine.
                self._state = self._DEALER
                if self._dealer_sprites:
                    for sprite in self._dealer_sprites:
                        if not sprite.card.face_up:
                            sprite.flip_reveal()
                            self.counter.register_card(sprite.card)
                            self.sounds.play("flip")
                    self._dealer_message(i18n.t("renderer.dealer_reveals"), cfg.COLOR_GOLD)
                self._dealer_seq_active = True
                self._dealer_seq_wait = self._dealer_pause(long=True)

            case GameState.PAYOUT:
                pass  # resultados llegan por on_round_end / on_round_end_players

            case GameState.GAME_OVER:
                # Fase 25: quedarse sin fichas en mitad de un Desafío es,
                # sencillamente, perderlo -- se reutiliza la detección de
                # bancarrota que ya existía (motivo de sobra: es la única
                # forma en que un Desafío puede terminar SIN que se acabe
                # de resolver una ronda con evaluate(), así que no hay
                # duplicar lógica de fichas aquí).
                if self._challenge is not None and self._challenge_result is None:
                    self._challenge_result = "lost"
                # Mismo motivo que en BETTING: no cortar la pantalla de
                # resultado si todavía se está mostrando.
                if self._state != self._RESULT:
                    self._state = self._GAMEOVER

    # ------------------------------------------------------------------
    # Secuenciador del reparto inicial multijugador
    # ------------------------------------------------------------------
    def _update_deal_sequence(self) -> None:
        """Avanza el reparto un jugador cada vez, esperando a que sus
        cartas terminen de volar antes de pasar al siguiente paso —
        igual que el secuenciador del turno del crupier, pero para el
        reparto inicial. Con un único jugador esto simplemente pacea sus
        dos cartas antes de mostrar los botones, sin cambios visibles."""
        if self._state != self._DEALING or not self._engine:
            return
        if self._engine.state != GameState.DEALING:
            return
        if any(s.is_animating for hand in self._player_sprites for s in hand):
            return
        if any(s.is_animating for s in self._dealer_sprites):
            return
        # En solitario no hay ningún otro asiento al que "dar paso", así
        # que en cuanto las cartas aterrizan se continúa sin más pausa —
        # la pausa entre pasos solo aporta algo cuando de verdad cambia el
        # foco de un jugador a otro (multijugador).
        if len(self._engine.players) > 1:
            if self._deal_seq_wait > 0:
                self._deal_seq_wait -= 1
                return
            self._deal_seq_wait = self._dealer_pause()
        self._engine.continue_round()

    def _on_round_end(self, payouts: list[HandPayout]) -> None:
        self._payouts = payouts
        self._result_timer = 180
        self._result_glows.clear()
        self._state = self._RESULT

        # Fase 25: con un Desafío activo, se comprueba tras CADA ronda si
        # ya se ha decidido (ganado/perdido) -- stats y chips ya están
        # actualizados en este punto (el motor resuelve el pago entero
        # antes de emitir on_round_end). El cambio de pantalla real a la
        # de fin de desafío se hace en _advance_from_result, igual que
        # GAME_OVER: no se corta la pantalla de resultado de esta última
        # mano de golpe.
        if self._challenge is not None and self._challenge_result is None:
            status = self._challenge.evaluate(self._engine.player.stats, self._engine.player.chips)
            if status != "in_progress":
                self._challenge_result = status

        # Actualizar contador con hole card ya revelada
        self.counter.update_deck_estimate(self._engine.deck)

        # Vuelo de fichas: hacia el contador de fichas del jugador si gana
        # en conjunto, hacia la zona del crupier si pierde, o se desvanecen
        # en su sitio si el neto es cero (empate / manos mixtas que cuadran).
        # En multijugador se usa el neto TOTAL de la mesa para decidir la
        # dirección — un simple acompañamiento visual, el desglose real de
        # quién gana o pierde se ve en el panel de resultado.
        if self._chip_tray:
            net_total = sum(p.net for p in payouts)
            if net_total > 0:
                target = self.table.get_chip_counter_pos()
            elif net_total < 0:
                target = self.table.get_house_pos()
            else:
                target = None
            self._chip_tray.fly_result(target)

        # Efectos de partículas + sonido según el resultado (si hay varias
        # manos —por split o por varios jugadores—, se usa el "mejor"
        # resultado del conjunto para el efecto)
        cx, cy = self.sw // 2, self.sh // 2
        results = [p.result for p in payouts]
        if RoundResult.BLACKJACK_WIN in results:
            self.particles.emit_blackjack(cx, cy - 80)
            self.hud.show_result(i18n.t("renderer.result_blackjack"), cfg.COLOR_BJ, icon="star")
            self.sounds.play("blackjack")
            self._trigger_zoom_flash()
        elif RoundResult.WIN in results or RoundResult.DEALER_BUST in results:
            self.particles.emit_win(cx, cy)
            self.hud.show_result(i18n.t("renderer.result_win"), cfg.COLOR_WIN, icon="check")
            self.sounds.play("win")
        elif RoundResult.LOSS in results:
            self.particles.emit_bust(cx, cy + 80)
            self.hud.show_result(i18n.t("renderer.result_loss"), cfg.COLOR_LOSE, icon="cross")
            self.sounds.play("bust")
        elif RoundResult.SURRENDER in results:
            self.hud.show_result(i18n.t("renderer.result_surrender"), cfg.COLOR_PUSH)
            self.sounds.play("push")
        else:
            self.hud.show_result(i18n.t("renderer.result_push"), cfg.COLOR_PUSH)
            self.sounds.play("push")

    def _on_round_end_players(self, payouts_by_player: list[list[HandPayout]]) -> None:
        """Desglose de resultados por jugador (multijugador) — se guarda
        aparte para el panel de resultado, que en modo un jugador sigue
        mostrando exactamente lo mismo que antes."""
        self._payouts_by_player = payouts_by_player

    def _on_achievements_unlocked(self, player_index: int, achievements: list) -> None:
        """Se acaban de desbloquear uno o más logros para `player_index`:
        se marcan como desbloqueados de inmediato (para que el panel F4 los
        refleje ya) y se encolan sus avisos, que se muestran uno detrás de
        otro en _update() para no amontonarlos si caen varios a la vez."""
        while len(self._unlocked_achievement_ids) <= player_index:
            self._unlocked_achievement_ids.append(set())
        for ach in achievements:
            self._unlocked_achievement_ids[player_index].add(ach.id)
            self._achievement_queue.append((player_index, ach))

    def _on_action_result(self, result: ActionResult) -> None:
        """Refresca los botones disponibles tras cada acción."""
        if self._btn_bar and self._engine.state == GameState.PLAYER_TURN:
            self._btn_bar.set_available(self._engine.get_available_actions())
        if result == ActionResult.BUST:
            self._trigger_shake()

    def _on_side_bets_result(self, player_index: int, outcomes: list) -> None:
        """Una o dos apuestas laterales de `player_index` se acaban de
        resolver (justo tras repartirle sus 2 cartas iniciales). Se
        muestra un aviso flotante por cada una y, si alguna ha ganado, un
        sonido de premio -- independiente de cómo acabe luego la mano
        principal, que se resuelve por separado al final de la ronda."""
        base_y = self.sh // 2 - 130
        any_won = False
        for i, outcome in enumerate(outcomes):
            kind_label = i18n.t("renderer.sidebet_perfect_pairs") if outcome.kind == "perfect_pairs" else "21+3"
            outcome_label = i18n.side_bet_label(outcome.label)
            if outcome.won:
                any_won = True
                text = f"{kind_label}: {outcome_label} -> +{outcome.net:.0f}"
                color = cfg.COLOR_WIN
            else:
                text = f"{kind_label}: {outcome_label}"
                color = (150, 150, 150)
            self.hud.add_message(text, self.sw // 2, base_y - i * 26, color)
        if any_won:
            self.sounds.play("win")

    def _on_engine_message(self, msg: str) -> None:
        self.hud.add_message(msg, self.sw//2, self.sh//2 - 60, cfg.COLOR_GOLD)
        if msg == i18n.t("engine.reshuffling"):
            self.sounds.play("shuffle")
            self._trigger_shuffle_fx()

    def _trigger_shuffle_fx(self) -> None:
        """Pequeña animación de cartas boca abajo abriéndose en abanico
        junto al indicador del zapato, para acompañar visualmente el
        rebarajado (además del toast de texto y el sonido)."""
        back = self.card_gen.get_back()
        small = pygame.transform.smoothscale(
            back, (max(1, int(cfg.CARD_WIDTH * 0.55)), max(1, int(cfg.CARD_HEIGHT * 0.55)))
        )
        cx, cy = self.sw - 100, self.sh - 108
        self._shuffle_fx.append(ShuffleEffect(cx, cy, small))

    # ------------------------------------------------------------------
    # Efectos de cámara
    # ------------------------------------------------------------------
    def _trigger_shake(self, mag: float = 9.0, frames: int = 16) -> None:
        self._shake_time = frames
        self._shake_mag  = mag

    def _trigger_zoom_flash(self, frames: int = 26) -> None:
        self._zoom_time  = frames
        self._zoom_total = frames

    # Un sonido distinto por cada acción de mano, en vez del "click"
    # genérico -- cada decisión se "siente" un poco distinta.
    _ACTION_SOUNDS = {
        "hit": "act_hit", "stand": "act_stand", "double": "act_double",
        "split": "act_split", "surrender": "act_surrender",
    }

    _TRAINING_LABEL_KEYS = {
        "hit": "renderer.action_hit", "stand": "renderer.action_stand", "double": "renderer.action_double",
        "split": "renderer.action_split", "surrender": "renderer.action_surrender",
    }

    def _on_player_action(self, action: str) -> None:
        if cfg.TRAINING_MODE:
            self._check_training_play(action)
        self.sounds.play(self._ACTION_SOUNDS.get(action, "button"))
        if action == "split":
            self._pre_split_sprites()

        # Se guarda la referencia a la mano ANTES de procesar la acción
        # (si es un double) porque el objeto se muta en el sitio -- así,
        # aunque el motor avance el índice de mano activa del jugador,
        # se puede seguir leyendo su valor final más abajo. Para un split
        # se guarda en cambio el jugador + el índice donde van a quedar
        # las dos manos nuevas (hand1 en ese índice, hand2 justo después),
        # ya que ANTES del split solo hay una mano y no hay nada útil que
        # leer todavía.
        doubling_hand = (self._engine.player.active_hand
                          if action == "double" and self._engine else None)
        doubling_player_name = self._engine.player.name if doubling_hand else None

        splitting_player = self._engine.player if action == "split" and self._engine else None
        splitting_player_name = splitting_player.name if splitting_player else None
        splitting_hand_index = splitting_player.active_hand_index if splitting_player else None

        self._engine.player_action(action)

        # Doblar en multijugador termina la mano al instante -- una única
        # carta y a plantarse -- justo cuando esa carta acaba de
        # repartirse. El motor (ver player_action en game_engine.py)
        # difiere en este caso el paso al siguiente jugador y se queda
        # esperando; aquí se detecta esa espera y se pausa un par de
        # segundos (más que la pausa corta del Blackjack natural, porque
        # aquí SÍ acaba de llegar una carta nueva que hay que poder ver)
        # antes de continuar sola la partida.
        if (doubling_hand is not None and self._state == self._PLAYING and self._engine
                and self._engine.state == GameState.PLAYER_TURN
                and self._engine.player.active_hand is None
                and len(self._engine.players) > 1):
            self._turn_reveal_wait = self._double_reveal_pause()
            self._turn_reveal_reason = "double"
            if doubling_hand.is_bust:
                self._player_message(
                    i18n.t("renderer.double_and_bust", name=doubling_player_name, value=doubling_hand.value),
                    cfg.COLOR_LOSE)
            else:
                self._player_message(
                    i18n.t("renderer.double_result", name=doubling_player_name, value=doubling_hand.value),
                    cfg.COLOR_GOLD)

        # Splitear Ases con hit_split_aces=False (el valor por defecto en
        # casi todos los presets) planta las DOS manos nuevas al instante,
        # con una sola carta cada una -- el mismo problema que el double:
        # sin esta pausa, el foco saltaría al siguiente jugador antes de
        # que se llegasen a ver esas cartas. Se reutiliza el mecanismo del
        # double (misma duración de pausa) con un motivo propio para que
        # la tira de asientos muestre el texto correcto (ver
        # _seat_status_text) en vez de "DOBLA".
        elif (splitting_player is not None and self._state == self._PLAYING and self._engine
                and self._engine.state == GameState.PLAYER_TURN
                and self._engine.player is splitting_player
                and self._engine.player.active_hand is None
                and len(self._engine.players) > 1
                and splitting_hand_index is not None
                and splitting_hand_index + 1 < len(splitting_player.hands)):
            hand1 = splitting_player.hands[splitting_hand_index]
            hand2 = splitting_player.hands[splitting_hand_index + 1]
            self._turn_reveal_wait = self._double_reveal_pause()
            self._turn_reveal_reason = "split_aces"
            self._player_message(
                i18n.t("renderer.split_aces_result", name=splitting_player_name,
                       v1=hand1.value, v2=hand2.value),
                cfg.COLOR_GOLD)

    def _check_training_play(self, action: str) -> None:
        """Modo entrenamiento (Fase 19): compara la acción que el jugador
        está a punto de tomar con la estrategia básica ANTES de aplicarla
        (la mano cambia en cuanto se llama a player_action), actualiza el
        marcador de la sesión y muestra feedback inmediato."""
        if self._engine.state != GameState.PLAYER_TURN:
            return
        hand = self._engine.player.active_hand
        if hand is None or hand.is_finished:
            return
        try:
            best = recommended_play(hand, self._engine.dealer.upcard_value, self._engine.rules)
        except Exception:
            return

        self._training_total += 1
        if action == best:
            self._training_correct += 1
            self._training_feedback = (i18n.t("renderer.training_correct"), cfg.COLOR_WIN, self._TRAINING_FEEDBACK_TOTAL)
        else:
            best_key = self._TRAINING_LABEL_KEYS.get(best)
            best_label = i18n.t(best_key) if best_key else best
            self._training_feedback = (
                i18n.t("renderer.training_should_have", label=best_label), (220, 150, 0), self._TRAINING_FEEDBACK_TOTAL,
            )

    def _pre_split_sprites(self) -> None:
        """Reparte físicamente los sprites de la pareja actual en dos
        montones ANTES de pedirle el split al motor.

        El motor, al resolver un split, solo emite on_card_dealt para la
        carta NUEVA de cada mano (la que se reparte de verdad) -- las dos
        cartas que ya estaban repartidas simplemente se redistribuyen
        entre las dos Hand resultantes, sin ningún evento de por medio.
        Si no hacemos nada aquí, esas dos cartas originales se quedan tal
        cual en `_player_sprites[idx]` (el montón de siempre) y solo la
        carta nueva de la segunda mano aparece en el montón nuevo -- de
        ahí que se viera como si el split moviera TODAS las cartas hacia
        la izquierda, con la mano derecha empezando con una sola carta en
        vez de con la segunda mitad de la pareja.

        La solución: separar YA los dos sprites existentes en dos listas
        (uno se queda en la mano de siempre, el otro pasa a ser la
        primera carta de la mano nueva justo al lado), para que cuando el
        motor reparta la carta nueva de cada mano, cada una caiga en su
        montón correcto -- y de paso se vea la segunda carta de la pareja
        deslizarse a su nuevo sitio, como cabría esperar."""
        idx = self._engine.player.active_hand_index
        if idx >= len(self._player_sprites) or len(self._player_sprites[idx]) != 2:
            return  # estado inesperado: no forzamos nada, mejor no romper nada
        first, second = self._player_sprites[idx]
        self._player_sprites[idx] = [first]
        self._player_sprites.insert(idx + 1, [second])

    def _on_insurance_answer(self, answer: str) -> None:
        self.sounds.play("button")
        self._engine.accept_insurance(answer == "yes")

    # ──────────────────────────────────────────────────────────────────
    # Update
    # ──────────────────────────────────────────────────────────────────
    def _update(self) -> None:
        # Sprites
        for s in self._dealer_sprites:
            s.update()
        for hand in self._player_sprites:
            for s in hand:
                s.update()

        # Partículas, fichas y HUD
        self.particles.update()
        self.hud.update()
        if self._chip_tray:
            self._chip_tray.update()

        # Feedback del modo entrenamiento (Fase 19): un único aviso, la
        # última jugada sustituye siempre a la anterior en vez de
        # amontonarse (ver _check_training_play).
        if self._training_feedback:
            text, color, frames = self._training_feedback
            frames -= 1
            self._training_feedback = (text, color, frames) if frames > 0 else None

        # Secuenciador del reparto inicial (multijugador: uno a uno)
        if self._state == self._DEALING:
            self._update_deal_sequence()

        # Secuenciador del turno del crupier
        if self._state == self._DEALER:
            self._update_dealer_sequence()

        # Pausa multijugador tras enseñar una mano sin ninguna acción
        # posible (Blackjack natural) — ver _on_state_change. Pasado el
        # tiempo de espera, el motor avanza solo a la siguiente mano/
        # jugador jugable.
        if self._state == self._PLAYING and self._turn_reveal_wait > 0 and self._engine:
            self._turn_reveal_wait -= 1
            if self._turn_reveal_wait <= 0:
                self._engine.continue_round()

        # Animación de barajado del zapato
        if self._shuffle_fx:
            self._shuffle_fx = [fx for fx in self._shuffle_fx if fx.update()]

        # Avisos de logros desbloqueados: uno detrás de otro
        if self._active_toast is not None:
            if not self._active_toast.update():
                self._active_toast = None
        if self._active_toast is None and self._achievement_queue:
            player_idx, ach = self._achievement_queue.pop(0)
            toast_name = (self._seat_names[player_idx]
                          if len(self._seat_names) > 1 and player_idx < len(self._seat_names)
                          else None)
            ach_name, ach_desc = i18n.achievement_text(ach)
            self._active_toast = AchievementToast(ach_name, ach_desc, ach.icon,
                                                    ach.color, player_name=toast_name)
            self.sounds.play("achievement")

        # Efectos de cámara
        if self._shake_time > 0:
            self._shake_time -= 1
        if self._zoom_time > 0:
            self._zoom_time -= 1

        # Temporizador de resultado
        if self._state == self._RESULT:
            self._result_timer -= 1
            if self._result_timer <= 0:
                self._advance_from_result()

    def _dealer_pause(self, long: bool = False) -> int:
        """Frames de espera entre pasos del crupier (y del reparto
        multijugador), con variación orgánica."""
        base = random.randint(28, 40) if long else random.randint(20, 34)
        return int(base / max(0.1, getattr(cfg, "ANIMATION_SPEED", 1.0)))

    def _double_reveal_pause(self) -> int:
        """Frames de espera tras doblar en multijugador antes de pasar el
        foco al siguiente jugador -- un par de segundos (más larga que
        _dealer_pause) para dar tiempo a ver bien la carta recibida."""
        base = random.randint(105, 125)   # ~1.75-2.1s a 60fps
        return int(base / max(0.1, getattr(cfg, "ANIMATION_SPEED", 1.0)))

    def _dealer_message(self, text: str, color: tuple) -> None:
        """Mensaje flotante de 'comentario en directo' del crupier, anclado
        justo debajo de su zona de cartas."""
        y = self.table.dealer_zone_y + cfg.CARD_HEIGHT + 34
        self.hud.add_message(text, self.sw // 2, y, color)

    def _player_message(self, text: str, color: tuple) -> None:
        """Mensaje flotante anclado justo DEBAJO de las cartas del jugador
        con el foco ahora mismo — paralelo a _dealer_message (que hace lo
        mismo bajo las cartas del crupier), usado en multijugador durante
        una pausa de turno (Blackjack natural, o al doblar — Fase 22).
        Debajo de las cartas hay hueco de sobra hasta la barra de botones
        (oculta mientras dura la pausa); ENCIMA, en cambio, el hueco entre
        el logo "BLACKJACK PAYS 3:2" de la mesa y la etiqueta fija "TU
        MANO N" es demasiado estrecho para un mensaje flotante sin que se
        solape con uno de los dos."""
        y = self.table.get_player_card_y() + cfg.CARD_HEIGHT + 34
        self.hud.add_message(text, self.sw // 2, y, color)

    def _announce_dealer_outcome(self) -> None:
        """Mensaje contextual al terminar el turno del crupier (se planta,
        se pasa, o revela blackjack)."""
        dealer = self._engine.dealer
        if dealer.is_bust:
            self._dealer_message(i18n.t("renderer.dealer_busts"), cfg.COLOR_WIN)
        elif dealer.has_blackjack:
            self._dealer_message(i18n.t("renderer.dealer_blackjack"), cfg.COLOR_LOSE)
        else:
            self._dealer_message(i18n.t("renderer.dealer_stands", value=dealer.value), cfg.COLOR_TEXT)

    def _update_dealer_sequence(self) -> None:
        """Avanza el turno del crupier un paso cada vez que toca, esperando
        siempre a que las animaciones de las cartas en mesa terminen antes
        de revelar más información o pasar al resultado."""
        if not self._dealer_seq_active or not self._engine:
            return

        if any(s.is_animating for s in self._dealer_sprites):
            return

        if self._dealer_seq_wait > 0:
            self._dealer_seq_wait -= 1
            return

        if self._engine.dealer_needs_card():
            self._dealer_message(i18n.t("renderer.dealer_hits"), cfg.COLOR_TEXT)
            self._engine.dealer_deal_next_card()
            self._dealer_seq_wait = self._dealer_pause()
        else:
            self._dealer_seq_active = False
            self._announce_dealer_outcome()
            self._engine.finish_dealer_turn()

    def _advance_from_result(self) -> None:
        if self._challenge_result is not None:
            self.hud.clear_transient()
            self._state = self._CHALLENGE_END
        elif self._engine.state == GameState.GAME_OVER:
            self.hud.clear_transient()
            self._state = self._GAMEOVER
        elif self._engine.state == GameState.BETTING:
            self._apply_betting_reset()

    def _apply_betting_reset(self) -> None:
        """Limpieza al pasar a la fase de apuesta: retira cartas y fichas
        de la mesa y resetea el contador tras un rebarajado. Se llama al
        arrancar la partida, al pasar el turno de apostar de un jugador al
        siguiente, o al salir de la pantalla de resultado."""
        self._state = self._BETTING
        self._pending_bet = 0.0
        self._dealer_sprites.clear()
        self._player_sprites.clear()
        self._spotlight_player = None
        self.particles.clear()
        if self._chip_tray:
            self._chip_tray.clear_stack()
        if self._side_bet_panel:
            self._side_bet_panel.reset()
        # Rebarajado
        if self._engine.deck.reshuffle_flag is False:
            self.counter.reset()

    # ──────────────────────────────────────────────────────────────────
    # Draw
    # ──────────────────────────────────────────────────────────────────
    def _draw(self) -> None:
        surf = self._scene_surf

        # 1. Mesa base
        self.table.draw(surf)

        # 2. Etiquetas dinámicas (valores, fichas, reglas)
        self._draw_labels(surf)

        # 3. Fichas apostadas en mesa (visibles durante toda la mano, no
        #    solo en la fase de apuesta, que las dibuja como parte de la
        #    bandeja completa más abajo)
        if self._chip_tray and self._state != self._BETTING:
            self._chip_tray.draw_bet(surf)

        # 4. Sprites de cartas
        for s in self._dealer_sprites:
            s.draw(surf)
        for hand in self._player_sprites:
            for s in hand:
                s.draw(surf)

        # 5. Partículas
        self.particles.draw(surf)

        # 5b. Animación de barajado (junto al indicador del zapato)
        for fx in self._shuffle_fx:
            fx.draw(surf)

        # 6. Controles según estado
        match self._state:
            case self._BETTING:
                self._draw_betting_ui(surf)
            case self._DEALING:
                self._draw_dealing_ui(surf)
            case self._PLAYING:
                if self._btn_bar and self._turn_reveal_wait <= 0:
                    self._btn_bar.draw(surf)
            case self._INSURANCE:
                if self._ins_bar:
                    msg = (i18n.t("renderer.even_money_or_insurance") if
                           (self._engine.player.active_hand and
                            self._engine.player.active_hand.is_blackjack)
                           else i18n.t("renderer.dealer_shows_ace"))
                    if len(self._engine.players) > 1:
                        msg = f"{self._engine.player.name}: {msg}"
                    self._ins_bar.draw(surf, msg)
            case self._RESULT:
                self._draw_result_overlay(surf)
            case self._GAMEOVER:
                self._draw_gameover(surf)
            case self._CHALLENGE_END:
                self._draw_challenge_end(surf)

        # 7. Tira de asientos (solo multijugador)
        if self._engine and len(self._engine.players) > 1:
            self._draw_seat_strip(surf)

        # 8. HUD (hints, contador, mensajes flotantes, banner, panel de logros)
        active_unlocked = (self._unlocked_achievement_ids[self._engine.active_player_index]
                            if self._engine and self._engine.active_player_index < len(self._unlocked_achievement_ids)
                            else set())
        # El banner de progreso del Desafío no aporta nada de más sobre la
        # propia pantalla de fin de Desafío (que ya repite ese mismo
        # nombre/cifras a tamaño completo) -- se oculta ahí para no
        # duplicar información.
        banner_challenge = self._challenge if self._state not in (self._GAMEOVER, self._CHALLENGE_END) else None
        self.hud.draw(surf, engine=self._engine, counter=self.counter,
                       unlocked_achievements=active_unlocked,
                       training_stats=(self._training_correct, self._training_total),
                       challenge=banner_challenge)

        # 8b. Feedback puntual del modo entrenamiento (encima del HUD normal,
        #     posición fija -- no sube ni se desvía como los mensajes flotantes)
        if self._training_feedback:
            self._draw_training_feedback(surf)

        # 9. Teclas de ayuda (esquina inferior derecha)
        self._draw_keybinds(surf)

        # 9b. Aviso de logro desbloqueado, por encima de todo lo demás
        if self._active_toast is not None:
            top_y = 16 if not (self._engine and len(self._engine.players) > 1) else 60
            self._active_toast.draw(surf, top_y=top_y)

        # 10. Componer la escena sobre la pantalla real (shake / zoom-flash)
        self._composite_scene()

    def _composite_scene(self) -> None:
        """Vuelca _scene_surf sobre self.screen aplicando temblor de cámara
        (bust) y/o zoom + destello dorado (blackjack) si están activos."""
        ox = oy = 0
        if self._shake_time > 0:
            fade = self._shake_time / 16.0
            m = self._shake_mag * min(1.0, fade)
            ox = random.randint(-int(m), int(m))
            oy = random.randint(-int(m), int(m))

        if self._zoom_time > 0 and self._zoom_total > 0:
            t = self._zoom_time / self._zoom_total
            k = math.sin(math.pi * (1.0 - t))   # 0 → 1 → 0
            scale = 1.0 + 0.07 * k
            w, h = max(1, int(self.sw * scale)), max(1, int(self.sh * scale))
            scaled = pygame.transform.smoothscale(self._scene_surf, (w, h))
            self.screen.blit(scaled, (ox - (w - self.sw) // 2, oy - (h - self.sh) // 2))
            alpha = int(80 * k)
            if alpha > 0:
                flash = pygame.Surface((self.sw, self.sh), pygame.SRCALPHA)
                flash.fill((255, 215, 0, alpha))
                self.screen.blit(flash, (0, 0))
        else:
            self.screen.blit(self._scene_surf, (ox, oy))
            if ox or oy:
                # Tapa el borde que el desplazamiento del temblor deja al descubierto
                pad = max(abs(ox), abs(oy)) + 2
                y_edge = 0 if oy >= 0 else self.sh - pad
                x_edge = 0 if ox >= 0 else self.sw - pad
                pygame.draw.rect(self.screen, cfg.COLOR_BG, (0, y_edge, self.sw, pad))
                pygame.draw.rect(self.screen, cfg.COLOR_BG, (x_edge, 0, pad, self.sh))

    # ------------------------------------------------------------------
    def _draw_labels(self, surf: pygame.Surface) -> None:
        if not self._engine:
            return
        engine = self._engine
        dealer = engine.dealer

        # Valor del crupier. Ojo: NO nos fiamos de engine.state para decidir
        # si la hole card sigue tapada -- el motor pasa a BETTING (ronda
        # siguiente) de forma síncrona nada más terminar la ronda, antes
        # de que la UI salga de la pantalla de resultado (ver
        # _on_state_change / _advance_from_result), así que engine.state
        # ya no refleja lo que se está mostrando en pantalla en ese
        # momento. La propia carta (¿boca arriba o no?) es la fuente de
        # verdad, siempre correcta sea cual sea el estado del motor.
        hole_hidden = (not dealer.hand.cards) or any(not c.face_up for c in dealer.hand.cards)
        if hole_hidden:
            d_val = f"{dealer.upcard_value} + ?"
        else:
            bj = " BJ" if dealer.has_blackjack else ""
            bust = " BUST" if dealer.is_bust else ""
            d_val = f"{dealer.value}{bj}{bust}"

        # Info de manos del jugador con el foco
        player_info = []
        for i, hand in enumerate(engine.player.hands):
            active = (i == engine.player.active_hand_index and
                      engine.state == GameState.PLAYER_TURN)
            soft = " soft" if hand.is_soft else ""
            bj   = " BJ" if hand.is_blackjack else ""
            bust = " BUST" if hand.is_bust else ""
            val_str = f"{hand.value}{soft}{bj}{bust}"
            player_info.append((val_str, active))

        if not player_info:
            player_info = [("", False)]

        self.table.draw_labels(
            surf,
            dealer_value=d_val,
            player_hands_info=player_info,
            chips=int(engine.player.chips),
            bet=int(self._pending_bet),
            rules_str=str(engine.rules),
            deck_info=i18n.t("renderer.shoe_info", remaining=engine.deck.cards_remaining, total=engine.deck.total_cards),
        )

    def _draw_betting_ui(self, surf: pygame.Surface) -> None:
        if not self._chip_tray or not self._engine:
            return
        rules  = self._engine.rules
        player = self._engine.player

        # Multijugador: deja claro a quién le toca apostar
        if len(self._engine.players) > 1:
            turn_txt = self._font_msg.render(i18n.t("renderer.betting_turn", name=player.name), True, cfg.COLOR_GOLD)
            surf.blit(turn_txt, (self.sw // 2 - turn_txt.get_width() // 2,
                                  int(self.sh * 0.42) - 96))

        self._chip_tray.draw(
            surf,
            current_bet=int(self._pending_bet),
            min_bet=int(rules.min_bet),
            max_bet=int(rules.max_bet),
            chips=int(player.chips),
        )

        if self._side_bet_panel:
            available = max(0.0, player.chips - self._pending_bet)
            self._side_bet_panel.clamp_to(rules.side_bet_max, available)
            self._side_bet_panel.draw(surf)

        # Botón DEAL
        if self._deal_btn:
            can_deal = self._pending_bet >= rules.min_bet
            col = cfg.COLOR_GOLD if (self._deal_hover and can_deal) else (
                  (120, 100, 30) if can_deal else (60, 60, 60))
            pygame.draw.rect(surf, (15, 12, 0), self._deal_btn, border_radius=8)
            pygame.draw.rect(surf, col, self._deal_btn, 2, border_radius=8)
            label_col = col if can_deal else (80, 80, 80)
            t = self._font_msg.render(i18n.t("renderer.deal_button"), True, label_col)
            icon_w = t.get_height() * 0.7
            group_w = t.get_width() + icon_w + 8
            tx = self._deal_btn.centerx - int(group_w) // 2
            ty = self._deal_btn.centery - t.get_height() // 2
            icons.triangle_right(surf, tx, self._deal_btn.centery, t.get_height() * 0.6, label_col)
            surf.blit(t, (tx + icon_w + 8, ty))

        # Botón REBET
        last_bet = self._last_bet_by_player.get(self._engine.active_player_index, 0.0)
        if self._rebet_btn and last_bet >= rules.min_bet:
            col2 = (160, 100, 220) if self._rebet_hover else (100, 60, 160)
            pygame.draw.rect(surf, (10, 5, 20), self._rebet_btn, border_radius=8)
            pygame.draw.rect(surf, col2, self._rebet_btn, 2, border_radius=8)
            t2 = self._font_small.render(i18n.t("renderer.rebet_button", amount=int(last_bet)), True, col2)
            icon_r2 = t2.get_height() * 0.42
            icon_w2 = icon_r2 * 2 + 6
            tx2 = self._rebet_btn.centerx - int(t2.get_width() + icon_w2) // 2
            ty2 = self._rebet_btn.centery - t2.get_height() // 2
            icons.refresh_arrow(surf, tx2 + icon_r2, self._rebet_btn.centery, icon_r2, col2)
            surf.blit(t2, (tx2 + icon_w2, ty2))

        # Instrucción
        hint = self._font_small.render(i18n.t("renderer.betting_hint"), True, (100, 100, 100))
        surf.blit(hint, (self.sw//2 - hint.get_width()//2, self.sh - 22))

    def _draw_dealing_ui(self, surf: pygame.Surface) -> None:
        """Mientras se reparte (sin botones ni fichas clicables). En
        multijugador aclara a quién le están repartiendo ahora mismo."""
        if not self._engine or len(self._engine.players) <= 1:
            return
        name = self._engine.player.name
        t = self._font_msg.render(i18n.t("renderer.dealing_to", name=name), True, cfg.COLOR_GOLD)
        surf.blit(t, (self.sw // 2 - t.get_width() // 2, int(self.sh * 0.42) - 96))

    def _draw_result_overlay(self, surf: pygame.Surface) -> None:
        """Panel semitransparente con el resultado de la ronda. En
        multijugador se agrupa por jugador; en solitario es exactamente el
        mismo panel de siempre (una línea por mano, sin nombres)."""
        multiplayer = self._engine and len(self._engine.players) > 1
        if multiplayer and self._payouts_by_player:
            self._draw_result_overlay_multi(surf)
            return

        if not self._payouts:
            return

        overlay = pygame.Surface((self.sw, self.sh), pygame.SRCALPHA)
        pygame.draw.rect(overlay, (0, 0, 0, 100),
                         pygame.Rect(self.sw//2 - 220, self.sh//2 - 110, 440, 220),
                         border_radius=16)
        surf.blit(overlay, (0, 0))

        y = self.sh//2 - 90
        for i, p in enumerate(self._payouts):
            label = _result_label(p.result)
            col   = RESULT_COLORS.get(p.result, cfg.COLOR_TEXT)
            hand_lbl = i18n.t("renderer.hand_n_label", n=i + 1) if len(self._payouts) > 1 else ""
            net_sign = "+" if p.net > 0 else ""
            line = f"{hand_lbl}{label}   {net_sign}{int(p.net)}"
            t = self._font_msg.render(line, True, col)
            surf.blit(t, (self.sw//2 - t.get_width()//2, y))
            y += 42

        if len(self._payouts) > 1:
            total = sum(p.net for p in self._payouts)
            sign  = "+" if total > 0 else ""
            total_col = cfg.COLOR_WIN if total > 0 else (cfg.COLOR_LOSE if total < 0 else cfg.COLOR_PUSH)
            tline = self._font_msg.render(i18n.t("renderer.total_label", sign=sign, amount=int(total)), True, total_col)
            surf.blit(tline, (self.sw//2 - tline.get_width()//2, y + 4))
            y += 42

        cont = self._font_small.render(i18n.t("renderer.continue_hint"), True, (120, 120, 120))
        surf.blit(cont, (self.sw//2 - cont.get_width()//2, self.sh//2 + 100))

    def _draw_result_overlay_multi(self, surf: pygame.Surface) -> None:
        """Panel de resultado con el desglose de CADA jugador, para partidas
        multijugador."""
        names = self._seat_names
        rows: list[tuple[str, str, tuple, float]] = []   # (name, label, color, net)
        for i, payouts in enumerate(self._payouts_by_player):
            name = names[i] if i < len(names) else i18n.t("renderer.player_n_fallback", n=i + 1)
            if not payouts:
                continue
            net = sum(p.net for p in payouts)
            if len(payouts) == 1:
                label = _result_label(payouts[0].result)
                col = RESULT_COLORS.get(payouts[0].result, cfg.COLOR_TEXT)
            else:
                label = i18n.t("renderer.n_hands", n=len(payouts))
                col = cfg.COLOR_WIN if net > 0 else (cfg.COLOR_LOSE if net < 0 else cfg.COLOR_PUSH)
            rows.append((name, label, col, net))

        row_h = 40
        box_w, box_h = 460, len(rows) * row_h + 64
        x0 = self.sw // 2 - box_w // 2
        y0 = self.sh // 2 - box_h // 2

        overlay = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        pygame.draw.rect(overlay, (0, 0, 0, 130), overlay.get_rect(), border_radius=16)
        pygame.draw.rect(overlay, cfg.COLOR_GOLD, overlay.get_rect(), 1, border_radius=16)
        surf.blit(overlay, (x0, y0))

        title = self._font_msg.render(i18n.t("renderer.round_result_title"), True, cfg.COLOR_GOLD)
        surf.blit(title, (self.sw // 2 - title.get_width() // 2, y0 + 14))

        y = y0 + 58
        for name, label, col, net in rows:
            sign = "+" if net > 0 else ""
            name_s = self._font_small.render(name, True, cfg.COLOR_TEXT)
            res_s = self._font_small.render(label, True, col)
            net_s = self._font_small.render(f"{sign}{int(net)}", True, col)
            surf.blit(name_s, (x0 + 24, y))
            surf.blit(res_s, (x0 + box_w // 2 - res_s.get_width() // 2, y))
            surf.blit(net_s, (x0 + box_w - 24 - net_s.get_width(), y))
            y += row_h

        cont = self._font_small.render(i18n.t("renderer.continue_hint"), True, (170, 170, 170))
        surf.blit(cont, (self.sw//2 - cont.get_width()//2, y0 + box_h + 14))

    def _draw_gameover(self, surf: pygame.Surface) -> None:
        """Pantalla de game over (solo alcanzable en modo un jugador)."""
        overlay = pygame.Surface((self.sw, self.sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surf.blit(overlay, (0, 0))

        t1 = self._font_big.render(i18n.t("renderer.game_over_title"), True, cfg.COLOR_LOSE)
        surf.blit(t1, (self.sw//2 - t1.get_width()//2, self.sh//2 - 120))

        if self._engine:
            s = self._engine.player.stats
            lines = [
                i18n.t("renderer.hands_played_stat", n=s.hands_played),
                i18n.t("renderer.wlp_stat", w=s.hands_won, l=s.hands_lost, p=s.hands_push),
                i18n.t("renderer.net_roi_stat", net=s.net_profit, roi=s.roi),
            ]
            y = self.sh//2 - 40
            for line in lines:
                t = self._font_msg.render(line, True, cfg.COLOR_TEXT)
                surf.blit(t, (self.sw//2 - t.get_width()//2, y))
                y += 38

        restart = self._font_msg.render(i18n.t("renderer.esc_to_menu"), True, (160, 160, 160))
        surf.blit(restart, (self.sw//2 - restart.get_width()//2, self.sh - 80))

    def _draw_challenge_end(self, surf: pygame.Surface) -> None:
        """Pantalla de fin de Desafío (Fase 25) -- ganado o perdido, según
        self._challenge_result. Mismo patrón visual que _draw_gameover."""
        overlay = pygame.Surface((self.sw, self.sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        surf.blit(overlay, (0, 0))

        won = self._challenge_result == "won"
        col = cfg.COLOR_WIN if won else cfg.COLOR_LOSE
        title_text = i18n.t("renderer.challenge_won_title") if won else i18n.t("renderer.challenge_lost_title")

        icon_cy = self.sh // 2 - 155
        if won:
            icons.check_mark(surf, self.sw // 2, icon_cy, 30, col, width=5)
        else:
            icons.cross_mark(surf, self.sw // 2, icon_cy, 26, col, width=5)

        t1 = self._font_big.render(title_text, True, col)
        surf.blit(t1, (self.sw // 2 - t1.get_width() // 2, self.sh // 2 - 118))

        if self._challenge is not None:
            challenge_name, _ = i18n.challenge_text(self._challenge)
            name_s = self._font_msg.render(challenge_name, True, cfg.COLOR_GOLD)
            surf.blit(name_s, (self.sw // 2 - name_s.get_width() // 2, self.sh // 2 - 62))

        if self._engine:
            s = self._engine.player.stats
            lines = [
                i18n.t("renderer.hands_played_stat", n=s.hands_played),
                i18n.t("renderer.wlp_stat", w=s.hands_won, l=s.hands_lost, p=s.hands_push),
                i18n.t("renderer.final_chips_net_stat", chips=int(self._engine.player.chips), net=s.net_profit),
            ]
            y = self.sh // 2 - 16
            for line in lines:
                t = self._font_msg.render(line, True, cfg.COLOR_TEXT)
                surf.blit(t, (self.sw // 2 - t.get_width() // 2, y))
                y += 34

        restart = self._font_msg.render(i18n.t("renderer.esc_to_menu"), True, (160, 160, 160))
        surf.blit(restart, (self.sw // 2 - restart.get_width() // 2, self.sh - 80))

    def _draw_seat_strip(self, surf: pygame.Surface) -> None:
        """Tira horizontal en la parte superior con un resumen de cada
        jugador de la mesa: avatar, nombre, fichas y estado actual — para
        que se vea de un vistazo a quién le toca. Solo se dibuja con más
        de un jugador; la partida en solitario no cambia visualmente."""
        engine = self._engine
        n = len(engine.players)
        card_w, card_h, gap = 210, 46, 10
        total_w = n * card_w + (n - 1) * gap
        x0 = self.sw // 2 - total_w // 2
        y0 = 8

        for i, player in enumerate(engine.players):
            r = pygame.Rect(x0 + i * (card_w + gap), y0, card_w, card_h)
            is_active = (i == engine.active_player_index)

            box = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
            bg_alpha = 70 if is_active else 30
            pygame.draw.rect(box, (0, 0, 0, bg_alpha + 60), box.get_rect(), border_radius=10)
            pygame.draw.rect(box, (212, 175, 55, 255) if is_active else (110, 110, 110, 180),
                              box.get_rect(), 2 if is_active else 1, border_radius=10)
            surf.blit(box, (r.x, r.y))

            shape, color = (self._seat_avatars[i] if i < len(self._seat_avatars)
                             else ("S", (212, 175, 55)))
            draw_avatar(surf, shape, color, r.x + 24, r.centery, 16)

            name = player.name if len(player.name) <= 12 else player.name[:11] + "…"
            name_col = cfg.COLOR_GOLD if is_active else cfg.COLOR_TEXT
            name_s = self._font_seat.render(name, True, name_col)
            surf.blit(name_s, (r.x + 46, r.y + 6))

            status = self._seat_status_text(i, player, is_active)
            status_s = self._font_seat_small.render(f"${int(player.chips)}  ·  {status}", True,
                                                      (200, 190, 140) if is_active else (150, 150, 150))
            surf.blit(status_s, (r.x + 46, r.y + 24))

    def _seat_status_text(self, index: int, player, is_active: bool) -> str:
        engine = self._engine
        if is_active:
            if self._state == self._PLAYING and self._turn_reveal_wait > 0:
                # Mano que se está enseñando un instante antes de pasar
                # sola al siguiente jugador -- por Blackjack natural (sin
                # ninguna acción posible), por acabar de doblar, o por
                # splitear Ases sin poder pedir más tras el split.
                if self._turn_reveal_reason == "double":
                    return i18n.t("renderer.seat_doubles")
                if self._turn_reveal_reason == "split_aces":
                    return i18n.t("renderer.seat_split_aces")
                return i18n.t("renderer.seat_blackjack")
            phase = {
                self._BETTING: i18n.t("renderer.status_betting"),
                self._DEALING: i18n.t("renderer.status_dealing"),
                self._INSURANCE: i18n.t("renderer.status_insurance"),
                self._PLAYING: i18n.t("renderer.status_playing"),
            }.get(self._state, i18n.t("renderer.status_in_game"))
            return phase.upper()
        if not player.hands:
            return i18n.t("renderer.status_waiting")
        hand = player.active_hand or (player.hands[-1] if player.hands else None)
        if hand is None:
            return i18n.t("renderer.status_waiting")
        if hand.is_bust:
            return i18n.t("renderer.status_bust", value=hand.value)
        if hand.is_blackjack:
            return i18n.t("renderer.blackjack_bang")
        if hand.is_finished:
            return i18n.t("renderer.status_stood", value=hand.value)
        return i18n.t("renderer.status_hand_value", value=hand.value)

    _TRAINING_FEEDBACK_TOTAL = 70

    def _draw_training_feedback(self, surf: pygame.Surface) -> None:
        text, color, frames = self._training_feedback
        alpha = int(255 * min(1.0, frames / self._TRAINING_FEEDBACK_TOTAL))
        s = self._font_msg.render(text, True, color)
        s.set_alpha(alpha)
        x = self.sw // 2 - s.get_width() // 2
        y = self.sh // 2 - 96
        surf.blit(s, (x, y))

    def _draw_keybinds(self, surf: pygame.Surface) -> None:
        lines = [i18n.t("renderer.keybinds_hint")]
        y = 8
        for line in lines:
            t = self._font_small.render(line, True, (70, 70, 70))
            surf.blit(t, (self.sw - t.get_width() - 10, y))
            y += 16


# ──────────────────────────────────────────────────────────────────────
# Punto de entrada standalone
# ──────────────────────────────────────────────────────────────────────
def launch() -> None:
    renderer = Renderer()
    renderer.run()


if __name__ == "__main__":
    launch()
