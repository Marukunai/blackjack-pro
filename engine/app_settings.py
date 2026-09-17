# engine/app_settings.py
# Ajustes globales de la aplicación (NO por perfil): tema visual (mesa +
# reverso de carta, Fase 15) y volumen/activación de audio (Fase 16).
# Se guardan en saves/app_settings.json, separado de profiles.db porque
# son preferencias del dispositivo/instalación -- todos los perfiles
# locales comparten el mismo tema y el mismo volumen, a diferencia de las
# fichas o el historial, que son por perfil.
# -------------------------------------------------------------
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

SETTINGS_PATH = Path("saves/app_settings.json")

# None en music_volume/sfx_volume/music_enabled/sfx_enabled significa
# "usar el valor por defecto de config/settings.py" -- así una instalación
# nueva, sin app_settings.json todavía, se comporta exactamente igual que
# antes de que existiera este módulo.
_DEFAULTS: dict[str, Any] = {
    "table_theme": "classic_green",
    "card_back_theme": "green_gold",
    "music_volume": None,
    "sfx_volume": None,
    "music_enabled": None,
    "sfx_enabled": None,
    # Fase 26 (ampliado a 5 idiomas en la Fase 27): idioma de la interfaz
    # ("es"/"en"/"fr"/"pt"/"de"). None = usar el valor por defecto de
    # config/settings.py (LANGUAGE = "es"), igual que el resto de ajustes
    # -- una instalación nueva sin app_settings.json se comporta
    # exactamente igual que antes de que existiera el idioma.
    "language": None,
}


class AppSettings:
    """Pequeño almacén JSON de preferencias globales. Tolerante a fallos:
    si el archivo no existe, está corrupto, o no se puede escribir (disco
    de solo lectura, permisos...), se usan/mantienen los valores por
    defecto en memoria sin romper la partida."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path or SETTINGS_PATH
        self._data: dict[str, Any] = dict(_DEFAULTS)
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return
        if isinstance(data, dict):
            for key in _DEFAULTS:
                if key in data:
                    self._data[key] = data[key]

    def _save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
        except OSError:
            pass

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        if key not in _DEFAULTS:
            raise KeyError(f"Ajuste desconocido: {key!r}")
        self._data[key] = value
        self._save()


_settings: Optional[AppSettings] = None


def get_settings() -> AppSettings:
    global _settings
    if _settings is None:
        _settings = AppSettings()
    return _settings
