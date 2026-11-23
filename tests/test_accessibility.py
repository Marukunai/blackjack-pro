# tests/test_accessibility.py
# Cobertura de la Fase 41 (accesibilidad básica: tamaño de letra y alto
# contraste) -- config/settings.py::apply_font_scale/apply_high_contrast
# y su persistencia en engine/app_settings.py no tenían ningún test
# permanente, igual que el resto de "valores efectivos mutables" del
# módulo (apply_table_theme/apply_card_back_theme) tampoco lo tenían.
#
# apply_font_scale()/apply_high_contrast() mutan atributos a nivel de
# MÓDULO de config/settings.py (FONT_SCALE, COLOR_TEXT, COLOR_GOLD...) --
# el mismo patrón que ya usan los temas visuales. Como pytest ejecuta
# todos los archivos de test en el mismo proceso, cualquier test de aquí
# que cambie ese estado global y no lo deje como lo encontró podría
# "contaminar" otros tests de la suite (ninguno depende hoy de los
# valores por defecto, pero mejor no arriesgarse) -- de ahí el fixture
# autouse que restaura "normal"/sin alto contraste después de cada test.
from __future__ import annotations

import pytest

from config import settings as cfg
from engine.app_settings import AppSettings


@pytest.fixture(autouse=True)
def _reset_accessibility_settings():
    yield
    cfg.apply_font_scale(cfg.DEFAULT_FONT_SCALE)
    cfg.apply_high_contrast(False)


class TestFontScale:
    def test_default_scale_is_one(self):
        assert cfg.FONT_SCALE_OPTIONS[cfg.DEFAULT_FONT_SCALE] == 1.0

    def test_apply_known_scale_updates_effective_value(self):
        assert cfg.apply_font_scale("large") is True
        assert cfg.CURRENT_FONT_SCALE == "large"
        assert cfg.FONT_SCALE == cfg.FONT_SCALE_OPTIONS["large"]

    def test_apply_unknown_scale_returns_false_and_changes_nothing(self):
        cfg.apply_font_scale("normal")
        assert cfg.apply_font_scale("huge") is False
        assert cfg.CURRENT_FONT_SCALE == "normal"
        assert cfg.FONT_SCALE == 1.0

    def test_scaled_font_size_scales_proportionally(self):
        cfg.apply_font_scale("normal")
        assert cfg.scaled_font_size(20) == 20
        cfg.apply_font_scale("large")
        assert cfg.scaled_font_size(20) == round(20 * cfg.FONT_SCALE_OPTIONS["large"])

    def test_scaled_font_size_never_returns_less_than_one_pixel(self):
        cfg.apply_font_scale("normal")
        assert cfg.scaled_font_size(0) >= 1
        assert cfg.scaled_font_size(-5) >= 1


class TestHighContrast:
    def test_disabled_by_default_state_matches_normal_colors(self):
        cfg.apply_high_contrast(False)
        assert cfg.HIGH_CONTRAST is False
        assert cfg.COLOR_TEXT == cfg._NORMAL_COLORS["COLOR_TEXT"]
        assert cfg.COLOR_BG == cfg._NORMAL_COLORS["COLOR_BG"]

    def test_enabling_switches_to_the_high_contrast_palette(self):
        cfg.apply_high_contrast(True)
        assert cfg.HIGH_CONTRAST is True
        assert cfg.COLOR_TEXT == (255, 255, 255)
        assert cfg.COLOR_BG == (0, 0, 0)
        assert cfg.COLOR_GOLD == cfg._HIGH_CONTRAST_COLORS["COLOR_GOLD"]
        assert cfg.COLOR_WIN == cfg._HIGH_CONTRAST_COLORS["COLOR_WIN"]
        assert cfg.COLOR_LOSE == cfg._HIGH_CONTRAST_COLORS["COLOR_LOSE"]
        assert cfg.COLOR_PUSH == cfg._HIGH_CONTRAST_COLORS["COLOR_PUSH"]

    def test_disabling_after_enabling_restores_the_original_colors(self):
        original_text = cfg._NORMAL_COLORS["COLOR_TEXT"]
        original_bg = cfg._NORMAL_COLORS["COLOR_BG"]
        cfg.apply_high_contrast(True)
        cfg.apply_high_contrast(False)
        assert cfg.COLOR_TEXT == original_text
        assert cfg.COLOR_BG == original_bg

    def test_accepts_truthy_non_bool_values(self):
        """app_settings.get('high_contrast') puede devolver None (nunca
        tocado) en vez de False -- apply_high_contrast() debe aceptar
        cualquier valor truthy/falsy, no solo bool estricto (así se usa
        en ui/renderer.py: apply_high_contrast(bool(app_settings.get(...))))."""
        cfg.apply_high_contrast(1)
        assert cfg.HIGH_CONTRAST is True
        cfg.apply_high_contrast(0)
        assert cfg.HIGH_CONTRAST is False


class TestAppSettingsPersistence:
    """Mismo patrón que el resto de AppSettings (table_theme, language...):
    None = nunca se tocó, así que una instalación nueva se comporta igual
    que antes de que existiera este ajuste."""

    def test_new_settings_file_has_no_accessibility_preference_yet(self, tmp_path):
        settings = AppSettings(path=tmp_path / "app_settings.json")
        assert settings.get("font_scale") is None
        assert settings.get("high_contrast") is None

    def test_font_scale_and_high_contrast_round_trip_through_disk(self, tmp_path):
        path = tmp_path / "app_settings.json"
        settings = AppSettings(path=path)
        settings.set("font_scale", "large")
        settings.set("high_contrast", True)

        reloaded = AppSettings(path=path)
        assert reloaded.get("font_scale") == "large"
        assert reloaded.get("high_contrast") is True

    def test_unknown_accessibility_key_is_rejected(self, tmp_path):
        settings = AppSettings(path=tmp_path / "app_settings.json")
        with pytest.raises(KeyError):
            settings.set("font_size", "large")   # nombre real de la clave es "font_scale"
