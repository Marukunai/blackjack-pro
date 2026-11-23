# tests/test_tutorial_screen.py
# Cobertura de ui/tutorial_screen.py (Fase 36, pantalla de "cómo
# jugar"): estructura de páginas, resolución de todas las claves de
# i18n en los 5 idiomas, y navegación. No comprueba el dibujado píxel
# a píxel (como el resto de pantallas Pygame de este proyecto), pero
# sí que ejecutar _draw() en cada página/idioma no lanza ninguna
# excepción -- que es exactamente lo que habría detectado una clave de
# i18n mal escrita o una página mal formada antes de llegar al jugador.
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from config import i18n
from config import settings as cfg


@pytest.fixture(scope="module", autouse=True)
def _pygame_display():
    pygame.init()
    pygame.display.set_mode((1280, 800))
    yield
    pygame.quit()


@pytest.fixture(autouse=True)
def _reset_language():
    original = getattr(cfg, "LANGUAGE", "es")
    yield
    cfg.LANGUAGE = original


def _make_screen():
    from ui.tutorial_screen import TutorialScreen
    return TutorialScreen(pygame.display.get_surface())


class TestPageStructure:
    def test_has_at_least_three_pages(self):
        from ui.tutorial_screen import TutorialScreen
        assert len(TutorialScreen.PAGES) >= 3

    def test_every_page_has_a_title_and_at_least_one_body_key(self):
        from ui.tutorial_screen import TutorialScreen
        for title_key, body_keys in TutorialScreen.PAGES:
            assert isinstance(title_key, str) and title_key
            assert isinstance(body_keys, list) and len(body_keys) >= 1

    def test_all_page_keys_resolve_in_every_language(self):
        """Ninguna clave usada por las páginas del tutorial debe faltar
        en ningún idioma (ni caer al propio nombre de la clave, lo que
        indicaría una traducción olvidada) -- mismo tipo de garantía que
        tests/test_i18n.py::TestKeyParity, pero específico de este set
        de claves nuevas."""
        from ui.tutorial_screen import TutorialScreen
        all_keys = {"menu.tutorial_button", "tutorial.title", "tutorial.hint",
                    "tutorial.back_button", "tutorial.prev_button", "tutorial.next_button"}
        for title_key, body_keys in TutorialScreen.PAGES:
            all_keys.add(title_key)
            all_keys.update(body_keys)

        for lang in ("es", "en", "fr", "pt", "de"):
            for key in all_keys:
                assert key in i18n.STRINGS[lang], f"falta {key!r} en {lang!r}"
                assert i18n.STRINGS[lang][key] != key

    def test_page_label_formats_with_placeholders(self):
        for lang in ("es", "en", "fr", "pt", "de"):
            cfg.LANGUAGE = lang
            text = i18n.t("tutorial.page_label", n=2, total=5)
            assert "2" in text and "5" in text


class TestNavigation:
    def test_starts_on_first_page(self):
        screen = _make_screen()
        assert screen._page == 0

    def test_next_advances_and_stops_at_last_page(self):
        screen = _make_screen()
        for _ in range(len(screen.PAGES) + 3):
            screen._go_next()
        assert screen._page == len(screen.PAGES) - 1

    def test_prev_retreats_and_stops_at_first_page(self):
        screen = _make_screen()
        screen._page = len(screen.PAGES) - 1
        for _ in range(len(screen.PAGES) + 3):
            screen._go_prev()
        assert screen._page == 0

    def test_escape_closes_the_screen(self):
        screen = _make_screen()
        screen._handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        assert screen._done is True

    def test_back_button_click_closes_the_screen(self):
        screen = _make_screen()
        screen._handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, pos=screen._back_rect.center, button=1))
        assert screen._done is True

    def test_right_arrow_key_advances_page(self):
        screen = _make_screen()
        screen._handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT))
        assert screen._page == 1

    def test_enter_on_last_page_closes_the_screen(self):
        screen = _make_screen()
        screen._page = len(screen.PAGES) - 1
        screen._handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        assert screen._done is True


class TestDrawingDoesNotCrash:
    def test_every_page_draws_without_raising_in_every_language(self):
        screen = _make_screen()
        for lang in ("es", "en", "fr", "pt", "de"):
            cfg.LANGUAGE = lang
            for i in range(len(screen.PAGES)):
                screen._page = i
                screen._draw()   # no debe lanzar excepción
