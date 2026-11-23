# tests/test_i18n.py
# Cobertura de config/i18n.py (5 idiomas, Fases 26-27) -- hasta esta fase
# no habia ningun test permanente que comprobara que los 5 idiomas se
# mantienen en paridad, ni ninguna regresion automatica del tipo de bug
# real corregido en la Fase 29 (una clave de traduccion mostrada en
# crudo en pantalla porque alguien olvido envolverla en i18n.t()).
from __future__ import annotations

import re

from config import settings as cfg
from config import i18n

LANGUAGES = ("es", "en", "fr", "pt", "de")

_PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")


def _placeholders(text: str) -> set[str]:
    return set(_PLACEHOLDER_RE.findall(text))


class TestKeyParity:
    def test_all_five_languages_define_the_same_keys(self):
        """Si alguien anade una clave nueva con _add() (es/en) pero se
        olvida de backfillear fr/pt/de (o viceversa), este test falla en
        vez de descubrirse a ojo jugando en ese idioma."""
        key_sets = {lang: set(i18n.STRINGS[lang].keys()) for lang in LANGUAGES}
        reference = key_sets["es"]
        for lang in LANGUAGES:
            missing = reference - key_sets[lang]
            extra = key_sets[lang] - reference
            assert not missing, f"'{lang}' le faltan claves: {sorted(missing)[:10]}"
            assert not extra, f"'{lang}' tiene claves de mas: {sorted(extra)[:10]}"

    def test_no_empty_translations(self):
        for lang in LANGUAGES:
            for key, value in i18n.STRINGS[lang].items():
                assert value != "", f"'{key}' esta vacio en '{lang}'"


class TestPlaceholderParity:
    def test_format_placeholders_match_across_languages(self):
        """Una traduccion con {value} en espanol pero {valor} (o nada) en
        otro idioma rompería t(key, **kwargs) solo en ese idioma -- esto
        se comprueba sin necesidad de disparar cada pantalla a mano."""
        es_strings = i18n.STRINGS["es"]
        for key, es_text in es_strings.items():
            expected = _placeholders(es_text)
            if not expected:
                continue
            for lang in LANGUAGES:
                actual = _placeholders(i18n.STRINGS[lang][key])
                assert actual == expected, (
                    f"'{key}' en '{lang}' tiene placeholders {actual}, "
                    f"se esperaba {expected}"
                )


class TestTranslationFunction:
    def test_t_falls_back_to_spanish_for_missing_key_in_other_language(self, monkeypatch):
        monkeypatch.setattr(cfg, "LANGUAGE", "en", raising=False)
        # Clave real que solo existe en es/en (no en fr/pt/de via _add directo
        # seria un mal ejemplo ya que la paridad ya se comprueba arriba);
        # en su lugar comprobamos el comportamiento de fallback ante una
        # clave que no existe en absoluto.
        assert i18n.t("clave.que.no.existe") == "clave.que.no.existe"

    def test_t_formats_kwargs(self, monkeypatch):
        monkeypatch.setattr(cfg, "LANGUAGE", "es", raising=False)
        assert i18n.t("engine.invalid_bet", min=5, max=500) == (
            i18n.STRINGS["es"]["engine.invalid_bet"].format(min=5, max=500)
        )

    def test_t_never_raises_on_missing_kwargs(self, monkeypatch):
        monkeypatch.setattr(cfg, "LANGUAGE", "es", raising=False)
        # Falta el kwarg 'min'/'max' a proposito: debe devolver la plantilla
        # sin reventar (ver el try/except de t()), no lanzar KeyError.
        result = i18n.t("engine.invalid_bet")
        assert isinstance(result, str) and result


class TestHandResultLabel:
    """Regresion directa del bug real corregido en la Fase 29: el banner
    de resultado de Repetir Mano mostraba la CLAVE de traduccion en vez
    del texto porque nunca se llamaba a i18n.t()."""

    RESULT_KEYS = ("WIN", "BLACKJACK_WIN", "DEALER_BUST", "LOSS", "PUSH", "SURRENDER")

    def test_known_result_keys_are_never_returned_raw(self, monkeypatch):
        for lang in LANGUAGES:
            monkeypatch.setattr(cfg, "LANGUAGE", lang, raising=False)
            for result_key in self.RESULT_KEYS:
                label = i18n.hand_result_label(result_key)
                assert label != result_key
                assert not label.startswith("history.")

    def test_unknown_result_key_falls_back_to_itself(self, monkeypatch):
        monkeypatch.setattr(cfg, "LANGUAGE", "es", raising=False)
        assert i18n.hand_result_label("ALGO_RARO") == "ALGO_RARO"


class TestSideBetLabel:
    def test_spanish_labels_pass_through_unchanged(self, monkeypatch):
        monkeypatch.setattr(cfg, "LANGUAGE", "es", raising=False)
        assert i18n.side_bet_label("Pareja perfecta") == "Pareja perfecta"

    def test_every_language_translates_every_known_side_bet_label(self, monkeypatch):
        known_labels = [
            "Color", "Escalera", "Escalera de color", "Pareja de color",
            "Pareja mixta", "Pareja perfecta", "Sin pareja", "Sin premio",
            "Trío", "Trío de color", "Damas de corazones",
            "Veinte del mismo palo", "Veinte cualquiera", "Pareja real",
            "Pareja del mismo palo",
        ]
        for lang in ("en", "fr", "pt", "de"):
            monkeypatch.setattr(cfg, "LANGUAGE", lang, raising=False)
            for label in known_labels:
                translated = i18n.side_bet_label(label)
                assert translated != label, f"'{label}' sin traducir en '{lang}'"
