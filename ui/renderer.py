# ui/renderer.py
# Bucle principal Pygame: ventana, game loop, eventos y render completo.
# Conecta GameEngine ↔ Table ↔ CardSprites ↔ Buttons ↔ HUD ↔ Animations.
# -------------------------------------------------------------
from __future__ import annotations

import sys
import pygame
from typing import Optional

from config import settings as cfg
from config.rules_presets import get_preset

from engine.game_engine import GameEngine
from engine.game_state import GameState, ActionResult, RoundResult
from engine.payout import HandPayout

from ai.card_counter import HiLoCounter

from ui.card_generator import CardGenerator
from ui.card_sprite import CardSprite
from ui.table import Table
from ui.buttons import ButtonBar, InsuranceBar
from ui.chip_stack import ChipTray
from ui.hud import HUD
from ui.animations import ParticleSystem, GlowEffect
from ui.menu import MainMenu


# ── Colores de resultado ──────────────────────────────────────────────
RESULT_COLORS = {
    RoundResult.WIN:          cfg.COLOR_WIN,
    RoundResult.BLACKJACK_WIN: cfg.COLOR_BJ,
    RoundResult.DEALER_BUST:  cfg.COLOR_WIN,
    RoundResult.LOSS:         cfg.COLOR_LOSE,
    RoundResult.PUSH:         cfg.COLOR_PUSH,
    RoundResult.SURRENDER:    cfg.COLOR_PUSH,
}
RESULT_LABELS = {
    RoundResult.WIN:           "✓  GANASTE",
    RoundResult.BLACKJACK_WIN: "★  BLACKJACK!",
    RoundResult.DEALER_BUST:   "✓  CRUPIER SE PASÓ",
    RoundResult.LOSS:          "✗  PERDISTE",
    RoundResult.PUSH:          "=  EMPATE",
    RoundResult.SURRENDER:     "~  RENDICIÓN",
}


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
    _PLAYING   = "playing"
    _INSURANCE = "insurance"
    _RESULT    = "result"
    _GAMEOVER  = "gameover"

    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption(cfg.WINDOW_TITLE)

        flags = pygame.FULLSCREEN if cfg.FULLSCREEN else 0
        self.screen = pygame.display.set_mode(
            (cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT), flags
        )
        self.clock = pygame.time.Clock()
        self.sw, self.sh = cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT

        # Subsistemas de UI
        self.table      = Table(self.sw, self.sh)
        self.card_gen   = CardGenerator()
        self.hud        = HUD(self.sw, self.sh)
        self.particles  = ParticleSystem()
        self.counter    = HiLoCounter()

        # Estado del renderer
        self._state   = self._MENU
        self._engine: Optional[GameEngine] = None

        # Sprites de cartas activos
        self._dealer_sprites: list[CardSprite] = []
        self._player_sprites: list[list[CardSprite]] = []  # [hand_idx][card_idx]

        # Apuesta en curso (fase betting)
        self._pending_bet: float = 0.0
        self._last_bet:    float = 0.0

        # Resultado pendiente de mostrar
        self._payouts: list[HandPayout] = []
        self._result_timer: int = 0
        self._result_glows: list[GlowEffect] = []

        # Botones (se crean tras conocer engine)
        self._btn_bar:       Optional[ButtonBar]    = None
        self._ins_bar:       Optional[InsuranceBar] = None
        self._chip_tray:     Optional[ChipTray]     = None
        self._deal_btn:      Optional[pygame.Rect]  = None
        self._deal_hover:    bool = False
        self._rebet_btn:     Optional[pygame.Rect]  = None
        self._rebet_hover:   bool = False

        # Fuentes auxiliares
        self._font_msg   = pygame.font.SysFont(None, 32, bold=True)
        self._font_small = pygame.font.SysFont(None, 20)
        self._font_big   = pygame.font.SysFont(None, 60, bold=True)

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
    # Menú principal
    # ──────────────────────────────────────────────────────────────────
    def _run_menu(self) -> None:
        menu = MainMenu(self.screen)
        player_name, preset_name = menu.run()
        self._start_game(player_name, preset_name)

    def _start_game(self, player_name: str, preset_name: str) -> None:
        rules = get_preset(preset_name)
        self._engine = GameEngine(rules=rules, player_name=player_name)
        self.counter  = HiLoCounter()
        self.counter._decks_estimate = float(rules.num_decks)

        # Registrar callbacks del engine
        self._engine.on("on_card_dealt",   self._on_card_dealt)
        self._engine.on("on_state_change", self._on_state_change)
        self._engine.on("on_round_end",    self._on_round_end)
        self._engine.on("on_action_result",self._on_action_result)
        self._engine.on("on_message",      self._on_engine_message)

        # Construir controles
        self._btn_bar   = ButtonBar(self.sw, self.sh, self._on_player_action)
        self._chip_tray = ChipTray(self.sw, self.sh, self._on_chip_click)
        self._deal_btn  = pygame.Rect(self.sw//2 - 80, self.sh - 70, 160, 44)
        self._rebet_btn = pygame.Rect(self.sw//2 + 90, self.sh - 70, 140, 44)

        self._dealer_sprites  = []
        self._player_sprites  = []
        self._pending_bet     = 0.0
        self._last_bet        = rules.min_bet

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

    def _confirm_bet(self) -> None:
        if self._pending_bet < self._engine.rules.min_bet:
            self.hud.add_message(
                f"Apuesta mínima: ${int(self._engine.rules.min_bet)}",
                self.sw//2, self.sh//2,
                cfg.COLOR_LOSE,
            )
            return
        self._last_bet = self._pending_bet
        ok = self._engine.place_bet(self._pending_bet)
        if ok:
            self._pending_bet = 0.0

    def _rebet(self) -> None:
        """Repite la última apuesta."""
        if self._last_bet >= self._engine.rules.min_bet:
            self._pending_bet = min(self._last_bet, self._engine.player.chips)
            self._confirm_bet()

    # ──────────────────────────────────────────────────────────────────
    # Callbacks del engine
    # ──────────────────────────────────────────────────────────────────
    def _on_card_dealt(self, card, target: str, hand_index: int) -> None:
        """Crea un CardSprite animado al repartir."""
        if target == "dealer":
            card_idx = len(self._dealer_sprites)
            tx = self.table.get_dealer_card_x(card_idx, card_idx + 1)
            ty = self.table.get_dealer_card_y()
            sprite = CardSprite(
                card, self.card_gen,
                target_x=tx, target_y=ty,
                start_x=self.sw//2, start_y=-cfg.CARD_HEIGHT,
                delay=card_idx * 4,
            )
            self._dealer_sprites.append(sprite)
            # Reposicionar cartas anteriores
            self._reposition_dealer_sprites()

        else:  # player
            # Asegurar que existe la lista para esta mano
            while len(self._player_sprites) <= hand_index:
                self._player_sprites.append([])

            card_idx = len(self._player_sprites[hand_index])
            num_hands = len(self._engine.player.hands)
            tx = self.table.get_player_card_x(card_idx, card_idx + 1,
                                               hand_index, num_hands)
            ty = self.table.get_player_card_y()
            sprite = CardSprite(
                card, self.card_gen,
                target_x=tx, target_y=ty,
                start_x=self.sw//2, start_y=self.sh + cfg.CARD_HEIGHT,
                delay=card_idx * 4,
            )
            self._player_sprites[hand_index].append(sprite)
            self._reposition_player_sprites()

        # Registrar en contador (solo cartas visibles)
        if card.face_up:
            self.counter.register_card(card)
        self.counter.update_deck_estimate(self._engine.deck)

    def _reposition_dealer_sprites(self) -> None:
        total = len(self._dealer_sprites)
        for i, sprite in enumerate(self._dealer_sprites):
            nx = self.table.get_dealer_card_x(i, total)
            ny = self.table.get_dealer_card_y()
            if abs(sprite.target_x - nx) > 2:
                sprite.move_to(nx, ny)

    def _reposition_player_sprites(self) -> None:
        num_hands = len(self._player_sprites)
        for hi, hand_sprites in enumerate(self._player_sprites):
            total = len(hand_sprites)
            for ci, sprite in enumerate(hand_sprites):
                nx = self.table.get_player_card_x(ci, total, hi, num_hands)
                ny = self.table.get_player_card_y()
                if abs(sprite.target_x - nx) > 2:
                    sprite.move_to(nx, ny)

    def _on_state_change(self, new_state: GameState) -> None:
        match new_state:
            case GameState.BETTING:
                self._state = self._BETTING
                self._pending_bet = 0.0
                self._dealer_sprites.clear()
                self._player_sprites.clear()
                self.particles.clear()
                # Rebarajado
                if self._engine.deck.reshuffle_flag is False:
                    self.counter.reset()

            case GameState.PLAYER_TURN:
                self._state = self._PLAYING
                if self._btn_bar:
                    self._btn_bar.set_available(self._engine.get_available_actions())

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
                # Revelar hole card
                if self._dealer_sprites:
                    for sprite in self._dealer_sprites:
                        if not sprite.card.face_up:
                            sprite.flip_reveal()
                            self.counter.register_card(sprite.card)

            case GameState.PAYOUT:
                pass  # resultados llegan por on_round_end

            case GameState.GAME_OVER:
                self._state = self._GAMEOVER

    def _on_round_end(self, payouts: list[HandPayout]) -> None:
        self._payouts = payouts
        self._result_timer = 180
        self._result_glows.clear()
        self._state = self._RESULT

        # Actualizar contador con hole card ya revelada
        self.counter.update_deck_estimate(self._engine.deck)

        # Efectos de partículas
        cx, cy = self.sw // 2, self.sh // 2
        for p in payouts:
            match p.result:
                case RoundResult.BLACKJACK_WIN:
                    self.particles.emit_blackjack(cx, cy - 80)
                    self.hud.show_result("★  BLACKJACK!", cfg.COLOR_BJ)
                case RoundResult.WIN | RoundResult.DEALER_BUST:
                    self.particles.emit_win(cx, cy)
                    self.hud.show_result("✓  GANASTE", cfg.COLOR_WIN)
                case RoundResult.LOSS:
                    self.particles.emit_bust(cx, cy + 80)
                    self.hud.show_result("✗  PERDISTE", cfg.COLOR_LOSE)
                case RoundResult.PUSH:
                    self.hud.show_result("=  EMPATE", cfg.COLOR_PUSH)
                case RoundResult.SURRENDER:
                    self.hud.show_result("~  RENDICIÓN", cfg.COLOR_PUSH)

    def _on_action_result(self, result: ActionResult) -> None:
        """Refresca los botones disponibles tras cada acción."""
        if self._btn_bar and self._engine.state == GameState.PLAYER_TURN:
            self._btn_bar.set_available(self._engine.get_available_actions())

    def _on_engine_message(self, msg: str) -> None:
        self.hud.add_message(msg, self.sw//2, self.sh//2 - 60, cfg.COLOR_GOLD)

    def _on_player_action(self, action: str) -> None:
        self._engine.player_action(action)

    def _on_insurance_answer(self, answer: str) -> None:
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

        # Partículas y HUD
        self.particles.update()
        self.hud.update()

        # Temporizador de resultado
        if self._state == self._RESULT:
            self._result_timer -= 1
            if self._result_timer <= 0:
                self._advance_from_result()

    def _advance_from_result(self) -> None:
        if self._engine.state == GameState.GAME_OVER:
            self._state = self._GAMEOVER
        elif self._engine.state == GameState.BETTING:
            self._state = self._BETTING

    # ──────────────────────────────────────────────────────────────────
    # Draw
    # ──────────────────────────────────────────────────────────────────
    def _draw(self) -> None:
        surf = self.screen

        # 1. Mesa base
        self.table.draw(surf)

        # 2. Etiquetas dinámicas (valores, fichas, reglas)
        self._draw_labels(surf)

        # 3. Sprites de cartas
        for s in self._dealer_sprites:
            s.draw(surf)
        for hand in self._player_sprites:
            for s in hand:
                s.draw(surf)

        # 4. Partículas
        self.particles.draw(surf)

        # 5. Controles según estado
        match self._state:
            case self._BETTING:
                self._draw_betting_ui(surf)
            case self._PLAYING:
                if self._btn_bar:
                    self._btn_bar.draw(surf)
            case self._INSURANCE:
                if self._ins_bar:
                    msg = ("¿Even Money o Seguro?" if
                           (self._engine.player.active_hand and
                            self._engine.player.active_hand.is_blackjack)
                           else "El crupier muestra As — ¿Seguro?")
                    self._ins_bar.draw(surf, msg)
            case self._RESULT:
                self._draw_result_overlay(surf)
            case self._GAMEOVER:
                self._draw_gameover(surf)

        # 6. HUD (hints, contador, mensajes flotantes, banner)
        self.hud.draw(surf, engine=self._engine, counter=self.counter)

        # 7. Teclas de ayuda (esquina inferior derecha)
        self._draw_keybinds(surf)

    # ------------------------------------------------------------------
    def _draw_labels(self, surf: pygame.Surface) -> None:
        if not self._engine:
            return
        engine = self._engine
        dealer = engine.dealer

        # Valor del crupier
        if engine.state in (GameState.PLAYER_TURN, GameState.INSURANCE,
                             GameState.DEALING, GameState.BETTING):
            d_val = f"{dealer.upcard_value} + ?"
        else:
            bj = " ★ BJ" if dealer.has_blackjack else ""
            bust = " BUST" if dealer.is_bust else ""
            d_val = f"{dealer.value}{bj}{bust}"

        # Info de manos del jugador
        player_info = []
        for i, hand in enumerate(engine.player.hands):
            active = (i == engine.player.active_hand_index and
                      engine.state == GameState.PLAYER_TURN)
            soft = " soft" if hand.is_soft else ""
            bj   = " ★" if hand.is_blackjack else ""
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
            deck_info=f"Zapato: {engine.deck.cards_remaining}/{engine.deck.total_cards}",
        )

    def _draw_betting_ui(self, surf: pygame.Surface) -> None:
        if not self._chip_tray or not self._engine:
            return
        rules  = self._engine.rules
        player = self._engine.player

        self._chip_tray.draw(
            surf,
            current_bet=int(self._pending_bet),
            min_bet=int(rules.min_bet),
            max_bet=int(rules.max_bet),
            chips=int(player.chips),
        )

        # Botón DEAL
        if self._deal_btn:
            can_deal = self._pending_bet >= rules.min_bet
            col = cfg.COLOR_GOLD if (self._deal_hover and can_deal) else (
                  (120, 100, 30) if can_deal else (60, 60, 60))
            pygame.draw.rect(surf, (15, 12, 0), self._deal_btn, border_radius=8)
            pygame.draw.rect(surf, col, self._deal_btn, 2, border_radius=8)
            label_col = col if can_deal else (80, 80, 80)
            t = self._font_msg.render("▶  DEAL", True, label_col)
            surf.blit(t, (self._deal_btn.centerx - t.get_width()//2,
                          self._deal_btn.centery - t.get_height()//2))

        # Botón REBET
        if self._rebet_btn and self._last_bet >= rules.min_bet:
            col2 = (160, 100, 220) if self._rebet_hover else (100, 60, 160)
            pygame.draw.rect(surf, (10, 5, 20), self._rebet_btn, border_radius=8)
            pygame.draw.rect(surf, col2, self._rebet_btn, 2, border_radius=8)
            t2 = self._font_small.render(f"↺  Repetir ${int(self._last_bet)}", True, col2)
            surf.blit(t2, (self._rebet_btn.centerx - t2.get_width()//2,
                           self._rebet_btn.centery - t2.get_height()//2))

        # Instrucción
        hint = self._font_small.render(
            "Haz clic en las fichas para apostar · Enter para repartir",
            True, (100, 100, 100)
        )
        surf.blit(hint, (self.sw//2 - hint.get_width()//2, self.sh - 22))

    def _draw_result_overlay(self, surf: pygame.Surface) -> None:
        """Panel semitransparente con el resultado de la ronda."""
        if not self._payouts:
            return

        # Fondo semitransparente
        overlay = pygame.Surface((self.sw, self.sh), pygame.SRCALPHA)
        pygame.draw.rect(overlay, (0, 0, 0, 100),
                         pygame.Rect(self.sw//2 - 220, self.sh//2 - 110, 440, 220),
                         border_radius=16)
        surf.blit(overlay, (0, 0))

        # Resultados por mano
        y = self.sh//2 - 90
        for i, p in enumerate(self._payouts):
            label = RESULT_LABELS.get(p.result, p.result.name)
            col   = RESULT_COLORS.get(p.result, cfg.COLOR_TEXT)
            hand_lbl = f"Mano {i+1}: " if len(self._payouts) > 1 else ""
            net_sign = "+" if p.net > 0 else ""
            line = f"{hand_lbl}{label}   {net_sign}{int(p.net)}"
            t = self._font_msg.render(line, True, col)
            surf.blit(t, (self.sw//2 - t.get_width()//2, y))
            y += 42

        # Total si hay splits
        if len(self._payouts) > 1:
            total = sum(p.net for p in self._payouts)
            sign  = "+" if total > 0 else ""
            total_col = cfg.COLOR_WIN if total > 0 else (cfg.COLOR_LOSE if total < 0 else cfg.COLOR_PUSH)
            tline = self._font_msg.render(f"Total: {sign}{int(total)}", True, total_col)
            surf.blit(tline, (self.sw//2 - tline.get_width()//2, y + 4))
            y += 42

        # Instrucción
        cont = self._font_small.render("Click o Enter para continuar", True, (120, 120, 120))
        surf.blit(cont, (self.sw//2 - cont.get_width()//2, self.sh//2 + 100))

    def _draw_gameover(self, surf: pygame.Surface) -> None:
        """Pantalla de game over."""
        overlay = pygame.Surface((self.sw, self.sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surf.blit(overlay, (0, 0))

        t1 = self._font_big.render("GAME OVER", True, cfg.COLOR_LOSE)
        surf.blit(t1, (self.sw//2 - t1.get_width()//2, self.sh//2 - 120))

        if self._engine:
            s = self._engine.player.stats
            lines = [
                f"Manos jugadas: {s.hands_played}",
                f"W / L / P:  {s.hands_won} / {s.hands_lost} / {s.hands_push}",
                f"Neto: {s.net_profit:+.0f}   ROI: {s.roi:+.1%}",
            ]
            y = self.sh//2 - 40
            for line in lines:
                t = self._font_msg.render(line, True, cfg.COLOR_TEXT)
                surf.blit(t, (self.sw//2 - t.get_width()//2, y))
                y += 38

        restart = self._font_msg.render("ESC → Menú principal", True, (160, 160, 160))
        surf.blit(restart, (self.sw//2 - restart.get_width()//2, self.sh - 80))

    def _draw_keybinds(self, surf: pygame.Surface) -> None:
        lines = ["F1: Hints  F2: Contador  F3: Stats  ESC: Menú"]
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