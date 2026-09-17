# ui/counting_trainer.py
# Fase 30: modo práctica de conteo de cartas (Hi-Lo).
#
# Reparte cartas de un zapato real (core.deck.Deck) a ritmo constante y,
# en puntos aleatorios, pausa y pregunta el running count actual,
# comprobándolo contra ai.card_counter.HiLoCounter -- el MISMO contador
# que ya usa el modo "avanzado" de la partida real (F6, SHOW_CARD_COUNTER
# en config/settings.py). La diferencia con ese modo es justo el punto
# de esto: aquí el conteo NUNCA se muestra en pantalla mientras se
# reparte -- el jugador tiene que llevarlo de cabeza, como en una mesa
# real, y solo se revela al final de cada pregunta.
#
# No toca GameEngine, fichas ni perfiles: es un ejercicio de
# entrenamiento aislado, como una app de flashcards. La única
# persistencia es la mejor marca personal (precisión/racha), guardada a
# nivel de dispositivo en engine/app_settings.py -- igual que el tema
# visual o el idioma, no es un dato de partida.
# -------------------------------------------------------------
from __future__ import annotations

import random
import pygame
from typing import Optional

from config import settings as cfg
from config import i18n
from core.deck import Deck
from ai.card_counter import HiLoCounter
from ui import icons
from ui.card_generator import CardGenerator
from engine.app_settings import get_settings

# (clave interna, frames por carta a 60fps) -- valores elegidos para que
# "Normal" se sienta parecido al ritmo de reparto de una partida real.
SPEED_OPTIONS: list[tuple[str, int]] = [
    ("slow", 90), ("normal", 55), ("fast", 32),
]
_SPEED_LABEL_KEYS = {
    "slow": "counting.speed_slow", "normal": "counting.speed_normal", "fast": "counting.speed_fast",
}
DECK_OPTIONS = Deck.VALID_DECK_COUNTS   # (1, 2, 4, 6, 8)

ASK_GAP_RANGE = (8, 14)   # cartas repartidas entre cada pregunta (al azar)
FEEDBACK_FRAMES = 100     # ~1.7s a 60fps antes de continuar solo
TRAIL_LEN = 4              # cartas pequeñas de "estela" a la izquierda de la actual


class CardCountingTrainer:
    """Bucle bloqueante con 5 estados: setup -> dealing -> asking ->
    feedback -> (dealing... | summary) -> (dealing tras 'Otra vez' | fin).
    run() no devuelve nada -- es una herramienta de entrenamiento aparte,
    no una elección que MainMenu necesite conocer."""

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.sw, self.sh = screen.get_size()
        self._done = False
        self._state = "setup"

        self._font_title  = pygame.font.SysFont(None, 38, bold=True)
        self._font_big    = pygame.font.SysFont(None, 30, bold=True)
        self._font_body   = pygame.font.SysFont(None, 22)
        self._font_small  = pygame.font.SysFont(None, 17)
        self._font_answer = pygame.font.SysFont(None, 56, bold=True)

        # ---- Pantalla de configuración: 2 filas ◄ valor ► (mismo widget
        # que usa RulesEditor) + par de botones Volver/Empezar. ----
        from ui.menu import _RuleRow  # import diferido: evita ciclo con ui.menu
        row_w, row_h, gap = 360, 44, 14
        rx = self.sw // 2 - row_w // 2
        ry = self.sh // 2 - 90
        self._deck_row = _RuleRow(
            "num_decks", "menu.field.num_decks", list(DECK_OPTIONS),
            lambda v: str(v), rx, ry, row_w, row_h, self._font_body)
        self._speed_row = _RuleRow(
            "speed", "counting.speed_label", [k for k, _ in SPEED_OPTIONS],
            lambda v: i18n.t(_SPEED_LABEL_KEYS[v]), rx, ry + row_h + gap, row_w, row_h, self._font_body)
        self._deck_row.set_value(1)
        self._speed_row.set_value("normal")
        self._setup_rows = [self._deck_row, self._speed_row]
        self._setup_row_idx = 0
        self._setup_rows[0].selected = True

        # Un único par de rects, reutilizado tal cual entre "setup"
        # (Volver / Empezar) y "summary" (Volver / Otra vez) -- mismo
        # sitio en pantalla en los dos estados, así la posición de
        # "Volver" es siempre la misma pase lo que pase.
        btn_y = ry + 2 * (row_h + gap) + 40
        self._left_rect  = pygame.Rect(self.sw // 2 - 230, btn_y, 220, 48)
        self._right_rect = pygame.Rect(self.sw // 2 + 10,  btn_y, 220, 48)
        self._left_hover = self._right_hover = False

        # ---- Estado de una sesión en curso (se crea en _start_session) ----
        self.card_gen = CardGenerator(width=150, height=210)
        self.deck: Optional[Deck] = None
        self.counter: Optional[HiLoCounter] = None
        self._speed_frames = 55
        self._frame_timer = 0
        self._cards_dealt = 0
        self._recent_cards: list = []      # estela visual, más reciente al final
        self._cards_since_ask = 0
        self._next_ask_gap = random.randint(*ASK_GAP_RANGE)
        self._end_after_feedback = False   # el zapato llegó a su corte justo al preguntar

        # ---- Pregunta/respuesta ----
        self._answer_input = ""
        self._last_given: Optional[int] = None
        self._last_correct: Optional[bool] = None
        self._feedback_timer = 0

        # ---- Estadísticas de la sesión ----
        self._questions_asked = 0
        self._questions_correct = 0
        self._streak = 0
        self._best_streak_session = 0
        self._new_record = False

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
            self._update()
            self._draw()
            pygame.display.flip()

    # ------------------------------------------------------------------
    # Transiciones
    # ------------------------------------------------------------------
    def _start_session(self) -> None:
        self.deck = Deck(num_decks=self._deck_row.value)
        self.counter = HiLoCounter()
        self._speed_frames = dict(SPEED_OPTIONS)[self._speed_row.value]
        self._frame_timer = 0
        self._cards_dealt = 0
        self._recent_cards = []
        self._cards_since_ask = 0
        self._next_ask_gap = random.randint(*ASK_GAP_RANGE)
        self._end_after_feedback = False

        self._questions_asked = 0
        self._questions_correct = 0
        self._streak = 0
        self._best_streak_session = 0
        self._new_record = False

        self._state = "dealing"

    def _end_session(self) -> None:
        """Va al resumen final, guardando un nuevo récord si procede
        (solo cuenta una sesión con al menos 1 pregunta respondida --
        salir de 'dealing' sin llegar a ninguna pregunta no cambia nada
        del historial de marcas)."""
        if self._questions_asked > 0:
            settings = get_settings()
            accuracy = self._questions_correct / self._questions_asked
            best_acc = settings.get("counting_best_accuracy")
            best_streak = settings.get("counting_best_streak", 0) or 0
            improved = False
            if best_acc is None or accuracy > best_acc:
                settings.set("counting_best_accuracy", accuracy)
                improved = True
            if self._best_streak_session > best_streak:
                settings.set("counting_best_streak", self._best_streak_session)
                improved = True
            self._new_record = improved
        self._state = "summary"

    def _ask_question(self) -> None:
        self._answer_input = ""
        self._state = "asking"

    def _submit_answer(self) -> None:
        if self._answer_input in ("", "-"):
            return   # nada que enviar todavía
        try:
            given = int(self._answer_input)
        except ValueError:
            return
        actual = self.counter.running_count
        correct = (given == actual)

        self._questions_asked += 1
        if correct:
            self._questions_correct += 1
            self._streak += 1
            self._best_streak_session = max(self._best_streak_session, self._streak)
        else:
            self._streak = 0

        self._last_given = given
        self._last_correct = correct
        self._feedback_timer = 0
        self._state = "feedback"

    def _resume_or_end(self) -> None:
        if self._end_after_feedback or self.deck.penetration_reached:
            self._end_session()
        else:
            self._cards_since_ask = 0
            self._next_ask_gap = random.randint(*ASK_GAP_RANGE)
            self._state = "dealing"

    # ------------------------------------------------------------------
    # Eventos
    # ------------------------------------------------------------------
    def _handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            self._left_hover = self._left_rect.collidepoint(event.pos)
            self._right_hover = self._right_rect.collidepoint(event.pos)

        if self._state == "setup":
            self._handle_setup_event(event)
        elif self._state == "asking":
            self._handle_asking_event(event)
        elif self._state in ("dealing", "feedback"):
            self._handle_dealing_or_feedback_event(event)
        elif self._state == "summary":
            self._handle_summary_event(event)

    def _handle_setup_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._done = True
            elif event.key == pygame.K_RETURN:
                self._start_session()
            elif event.key == pygame.K_UP:
                self._select_setup_row(self._setup_row_idx - 1)
            elif event.key == pygame.K_DOWN:
                self._select_setup_row(self._setup_row_idx + 1)
            elif event.key == pygame.K_LEFT:
                self._setup_rows[self._setup_row_idx].step(-1)
            elif event.key == pygame.K_RIGHT:
                self._setup_rows[self._setup_row_idx].step(1)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._left_rect.collidepoint(event.pos):
                self._done = True
                return
            if self._right_rect.collidepoint(event.pos):
                self._start_session()
                return
            for i, row in enumerate(self._setup_rows):
                if row.handle_event(event):
                    self._select_setup_row(i)

    def _select_setup_row(self, idx: int) -> None:
        idx = max(0, min(len(self._setup_rows) - 1, idx))
        for i, row in enumerate(self._setup_rows):
            row.selected = (i == idx)
        self._setup_row_idx = idx

    def _handle_dealing_or_feedback_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._end_session()
        elif self._state == "feedback" and event.type == pygame.KEYDOWN and \
                event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self._resume_or_end()
        elif self._state == "feedback" and event.type == pygame.MOUSEBUTTONDOWN:
            self._resume_or_end()

    def _handle_asking_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self._end_session()
        elif event.key == pygame.K_RETURN:
            self._submit_answer()
        elif event.key == pygame.K_BACKSPACE:
            self._answer_input = self._answer_input[:-1]
        elif event.unicode == "-" and self._answer_input == "":
            self._answer_input = "-"
        elif event.unicode.isdigit() and len(self._answer_input) < 4:
            self._answer_input += event.unicode

    def _handle_summary_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._done = True
            elif event.key == pygame.K_RETURN:
                self._start_session()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._left_rect.collidepoint(event.pos):
                self._done = True
            elif self._right_rect.collidepoint(event.pos):
                self._start_session()

    # ------------------------------------------------------------------
    # Actualización (solo "dealing" avanza solo, por tiempo)
    # ------------------------------------------------------------------
    def _update(self) -> None:
        if self._state == "dealing":
            self._frame_timer += 1
            if self._frame_timer >= self._speed_frames:
                self._frame_timer = 0
                self._deal_one()
        elif self._state == "feedback":
            self._feedback_timer += 1
            if self._feedback_timer >= FEEDBACK_FRAMES:
                self._resume_or_end()

    def _deal_one(self) -> None:
        card = self.deck.deal()
        self.counter.register_card(card)
        self.counter.update_deck_estimate(self.deck)
        self._cards_dealt += 1
        self._cards_since_ask += 1

        self._recent_cards.append(card)
        if len(self._recent_cards) > TRAIL_LEN + 1:
            self._recent_cards.pop(0)

        if self._cards_since_ask >= self._next_ask_gap:
            self._end_after_feedback = self.deck.penetration_reached
            self._ask_question()
        elif self.deck.penetration_reached:
            self._end_session()

    # ------------------------------------------------------------------
    # Dibujo
    # ------------------------------------------------------------------
    def _draw(self) -> None:
        surf = self.screen
        surf.fill(cfg.COLOR_BG)

        title = self._font_title.render(i18n.t("counting.title"), True, cfg.COLOR_GOLD)
        surf.blit(title, (self.sw // 2 - title.get_width() // 2, 28))

        if self._state == "setup":
            self._draw_setup(surf)
        elif self._state in ("dealing", "asking", "feedback"):
            self._draw_session(surf)
        elif self._state == "summary":
            self._draw_summary(surf)

    def _draw_setup(self, surf: pygame.Surface) -> None:
        for row in self._setup_rows:
            row.draw(surf)

        settings = get_settings()
        best_acc = settings.get("counting_best_accuracy")
        if best_acc is None:
            record_text = i18n.t("counting.no_record")
        else:
            best_streak = settings.get("counting_best_streak", 0) or 0
            record_text = i18n.t("counting.best_record", pct=f"{best_acc:.0%}", streak=best_streak)
        record = self._font_small.render(record_text, True, (170, 170, 170))
        surf.blit(record, (self.sw // 2 - record.get_width() // 2,
                            self._speed_row.rect.bottom + 20))

        self._draw_left_right_buttons(surf, i18n.t("counting.back_button"),
                                       i18n.t("counting.start_button"))

        hint = self._font_small.render(i18n.t("counting.hint_setup"), True, (90, 90, 90))
        surf.blit(hint, (self.sw // 2 - hint.get_width() // 2, self.sh - 40))

    def _draw_left_right_buttons(self, surf: pygame.Surface, left_text: str, right_text: str) -> None:
        left_col = cfg.COLOR_TEXT if self._left_hover else (150, 150, 150)
        pygame.draw.rect(surf, (20, 15, 0), self._left_rect, border_radius=10)
        pygame.draw.rect(surf, left_col, self._left_rect, 2, border_radius=10)
        lt = self._font_body.render(left_text, True, left_col)
        surf.blit(lt, (self._left_rect.centerx - lt.get_width() // 2,
                        self._left_rect.centery - lt.get_height() // 2))

        right_col = cfg.COLOR_GOLD if self._right_hover else (160, 130, 40)
        pygame.draw.rect(surf, (20, 15, 0), self._right_rect, border_radius=10)
        pygame.draw.rect(surf, right_col, self._right_rect, 2, border_radius=10)
        rt = self._font_body.render(right_text, True, right_col)
        surf.blit(rt, (self._right_rect.centerx - rt.get_width() // 2,
                        self._right_rect.centery - rt.get_height() // 2))

    # ------------------------------------------------------------------
    def _draw_session(self, surf: pygame.Surface) -> None:
        # Estela de las últimas cartas (todas menos la actual), pequeñas
        # y difuminadas a la izquierda de la carta grande -- da sensación
        # de ritmo sin ser una ayuda real para contar (no se ve el valor
        # Hi-Lo de cada una, solo la propia carta, igual que en una mesa).
        trail = self._recent_cards[:-1] if self._recent_cards else []
        small_w, small_h = 60, 84
        gap = 14
        total_trail_w = len(trail) * (small_w + gap)
        tx = self.sw // 2 - 90 - total_trail_w
        ty = self.sh // 2 - small_h // 2
        for card in trail:
            small = pygame.transform.smoothscale(self.card_gen.get(card.asset_name), (small_w, small_h))
            small.set_alpha(110)
            surf.blit(small, (tx, ty))
            tx += small_w + gap

        # Carta actual, centrada y grande.
        if self._recent_cards:
            current = self._recent_cards[-1]
            big = self.card_gen.get(current.asset_name)
            bx = self.sw // 2 - big.get_width() // 2
            by = self.sh // 2 - big.get_height() // 2
            shadow = pygame.Surface(big.get_size(), pygame.SRCALPHA)
            pygame.draw.rect(shadow, (0, 0, 0, 90), shadow.get_rect(), border_radius=10)
            surf.blit(shadow, (bx + 5, by + 7))
            surf.blit(big, (bx, by))

        dealt = self._font_small.render(
            i18n.t("counting.cards_dealt_label", n=self._cards_dealt), True, (140, 140, 140))
        surf.blit(dealt, (self.sw // 2 - dealt.get_width() // 2, self.sh // 2 + 130))

        if self._state == "asking":
            self._draw_asking_box(surf)
        elif self._state == "feedback":
            self._draw_feedback_box(surf)

        hint_key = "counting.answer_hint" if self._state == "asking" else "counting.hint_dealing"
        if self._state != "feedback":
            hint = self._font_small.render(i18n.t(hint_key), True, (90, 90, 90))
            surf.blit(hint, (self.sw // 2 - hint.get_width() // 2, self.sh - 40))

    def _draw_asking_box(self, surf: pygame.Surface) -> None:
        box_w, box_h = 520, 130
        box = pygame.Rect(self.sw // 2 - box_w // 2, self.sh - 216, box_w, box_h)
        panel = pygame.Surface((box.w, box.h), pygame.SRCALPHA)
        pygame.draw.rect(panel, (0, 0, 0, 210), panel.get_rect(), border_radius=12)
        pygame.draw.rect(panel, cfg.COLOR_GOLD, panel.get_rect(), 2, border_radius=12)
        surf.blit(panel, (box.x, box.y))

        prompt = self._font_body.render(i18n.t("counting.ask_prompt"), True, cfg.COLOR_TEXT)
        surf.blit(prompt, (box.centerx - prompt.get_width() // 2, box.y + 14))

        cursor = "▏" if (pygame.time.get_ticks() // 400) % 2 == 0 else " "
        answer_text = (self._answer_input or "") + cursor
        ans = self._font_answer.render(answer_text, True, cfg.COLOR_GOLD)
        surf.blit(ans, (box.centerx - ans.get_width() // 2, box.y + 48))

    def _draw_feedback_box(self, surf: pygame.Surface) -> None:
        box_w, box_h = 520, 130
        box = pygame.Rect(self.sw // 2 - box_w // 2, self.sh - 216, box_w, box_h)
        color = cfg.COLOR_WIN if self._last_correct else cfg.COLOR_LOSE
        panel = pygame.Surface((box.w, box.h), pygame.SRCALPHA)
        pygame.draw.rect(panel, (0, 0, 0, 210), panel.get_rect(), border_radius=12)
        pygame.draw.rect(panel, color, panel.get_rect(), 2, border_radius=12)
        surf.blit(panel, (box.x, box.y))

        if self._last_correct:
            icons.check_mark(surf, box.x + 34, box.y + 34, 16, color)
            title_key = "counting.feedback_correct"
        else:
            icons.cross_mark(surf, box.x + 34, box.y + 34, 16, color)
            title_key = "counting.feedback_wrong"
        title = self._font_big.render(i18n.t(title_key), True, color)
        surf.blit(title, (box.x + 60, box.y + 20))

        detail = self._font_body.render(
            i18n.t("counting.feedback_detail", given=self._last_given,
                   actual=self.counter.running_count),
            True, cfg.COLOR_TEXT)
        surf.blit(detail, (box.centerx - detail.get_width() // 2, box.y + 70))

        streak = self._font_small.render(f"🔥 {self._streak}" if self._streak > 1 else "", True, (200, 160, 60))
        if self._streak > 1:
            surf.blit(streak, (box.right - streak.get_width() - 14, box.y + 14))

    # ------------------------------------------------------------------
    def _draw_summary(self, surf: pygame.Surface) -> None:
        sub = self._font_big.render(i18n.t("counting.summary_title"), True, cfg.COLOR_TEXT)
        surf.blit(sub, (self.sw // 2 - sub.get_width() // 2, self.sh // 2 - 170))

        pct = (self._questions_correct / self._questions_asked) if self._questions_asked else 0.0
        lines = [
            i18n.t("counting.summary_questions", n=self._questions_asked),
            i18n.t("counting.summary_correct", n=self._questions_correct, pct=f"{pct:.0%}"),
            i18n.t("counting.summary_best_streak", n=self._best_streak_session),
        ]
        if self.counter is not None:
            lines.append(i18n.t("counting.summary_final_count",
                                 rc=f"{self.counter.running_count:+d}",
                                 tc=f"{self.counter.true_count:+.1f}"))
        y = self.sh // 2 - 110
        for line in lines:
            t = self._font_body.render(line, True, cfg.COLOR_TEXT)
            surf.blit(t, (self.sw // 2 - t.get_width() // 2, y))
            y += 32

        if self._new_record:
            rec = self._font_body.render(i18n.t("counting.summary_new_record"), True, cfg.COLOR_GOLD)
            surf.blit(rec, (self.sw // 2 - rec.get_width() // 2, y + 6))

        self._draw_left_right_buttons(surf, i18n.t("counting.back_button"),
                                       i18n.t("counting.retry_button"))

        hint = self._font_small.render(i18n.t("counting.hint_summary"), True, (90, 90, 90))
        surf.blit(hint, (self.sw // 2 - hint.get_width() // 2, self.sh - 40))
