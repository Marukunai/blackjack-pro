# engine/profile_backup.py
# Copia de seguridad / restauración de un perfil completo (Fase 32), a
# petición de Maruku como complemento natural de la exportación a CSV de
# la Fase 29 -- el CSV es de solo lectura (para abrir en Excel/Sheets),
# esto es un volcado JSON de ida y vuelta: perfil + historial completo +
# logros desbloqueados, pensado para guardar antes de reinstalar o para
# llevarse el progreso a otro equipo.
# -------------------------------------------------------------
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Optional

from config import settings as cfg
from engine.profile_store import get_store

BACKUPS_DIR = cfg.SAVES_DIR / "backups"

# Versión del formato del archivo de copia de seguridad -- si el esquema
# cambiara de forma incompatible en el futuro, import_profile_backup()
# puede usar este número para decidir cómo leer archivos antiguos en vez
# de romperse directamente.
BACKUP_FORMAT_VERSION = 1

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9 _-]+")

# Columnas de `profiles` que identifican la FILA, no al jugador -- no se
# restauran tal cual al importar (el perfil importado es una fila nueva).
_SKIP_COLUMNS = {"id"}


class BackupError(Exception):
    """Fallo al exportar o importar una copia de seguridad de perfil."""


def _safe_filename_part(name: str) -> str:
    cleaned = _SAFE_NAME_RE.sub("_", name).strip("_ ")
    return cleaned or "jugador"


def export_profile_backup(profile_id: int, out_dir: Optional[Path] = None) -> Path:
    """Exporta el perfil (datos + historial completo de manos + logros
    desbloqueados, con sus fechas originales) a un nuevo archivo JSON en
    `out_dir` (por defecto saves/backups/). Devuelve la ruta creada.
    Lanza BackupError si el perfil no existe."""
    store = get_store()
    profile = store.get_profile(profile_id)
    if profile is None:
        raise BackupError(f"profile_id {profile_id} no existe")

    target_dir = out_dir or BACKUPS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    profile_data = {k: v for k, v in profile.items() if k not in _SKIP_COLUMNS}
    data = {
        "backup_format": BACKUP_FORMAT_VERSION,
        "exported_at": time.time(),
        "app_version": cfg.APP_VERSION,
        "profile": profile_data,
        "hand_history": store.get_all_history(profile_id),
        "achievements": store.get_achievements_detail(profile_id),
    }

    stamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"blackjack_backup_{_safe_filename_part(profile['name'])}_{stamp}.json"
    path = target_dir / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def _parse_backup(path: Path) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise BackupError("No se pudo leer el archivo de copia de seguridad.") from exc

    if not isinstance(data, dict) or "profile" not in data:
        raise BackupError("El archivo no tiene el formato esperado de una copia de "
                           "seguridad de Blackjack Pro.")
    if data.get("backup_format", 0) > BACKUP_FORMAT_VERSION:
        raise BackupError("Esta copia de seguridad es de una versión más nueva del "
                           "juego -- actualiza Blackjack Pro antes de importarla.")
    return data


def preview_profile_backup(path: Path) -> dict:
    """Lee solo lo necesario para mostrar una vista previa antes de
    importar (nombre, fichas, nº de manos, fecha de exportación) sin
    tocar la base de datos -- para que la UI pueda preguntar "¿importar
    esto?" con contexto, en vez de a ciegas."""
    data = _parse_backup(path)
    profile = data["profile"]
    return {
        "name": profile.get("name", "?"),
        "chips": profile.get("chips", 0.0),
        "hands_played": profile.get("hands_played", 0),
        "hand_count": len(data.get("hand_history", [])),
        "achievement_count": len(data.get("achievements", [])),
        "exported_at": data.get("exported_at"),
    }


def import_profile_backup(path: Path, new_name: Optional[str] = None) -> int:
    """Crea un perfil NUEVO a partir de un archivo de copia de seguridad
    (nunca sobrescribe un perfil existente) y le restaura fichas,
    estadísticas, historial completo de manos y logros. Devuelve el
    profile_id del perfil recién creado. Lanza BackupError si el archivo
    no es válido o si el nombre ya está en uso y no se indicó `new_name`."""
    data = _parse_backup(path)
    store = get_store()
    profile = data["profile"]
    name = (new_name or profile.get("name") or "Jugador").strip() or "Jugador"

    avatar_color_str = profile.get("avatar_color", "212,175,55")
    try:
        r, g, b = (int(x) for x in avatar_color_str.split(","))
    except (ValueError, AttributeError):
        r, g, b = (212, 175, 55)

    try:
        profile_id = store.create_profile(
            name, profile.get("avatar_shape", "S"), (r, g, b),
            starting_chips=profile.get("chips", 1000.0),
        )
    except ValueError as exc:
        raise BackupError(
            f"Ya existe un perfil llamado '{name}' -- elige otro nombre para importar "
            f"esta copia de seguridad."
        ) from exc

    restore_fields = {
        k: v for k, v in profile.items()
        if k not in _SKIP_COLUMNS and k not in ("name", "avatar_shape", "avatar_color")
    }
    if restore_fields:
        store.save_stats(profile_id, restore_fields)

    for row in data.get("hand_history", []):
        store.import_hand_record(
            profile_id,
            played_at=row["played_at"],
            preset_name=row.get("preset_name"),
            bet=row["bet"],
            result=row["result"],
            net=row["net"],
            chips_after=row["chips_after"],
            replay_data=row.get("replay_data"),
        )

    for row in data.get("achievements", []):
        store.import_achievement(profile_id, row["achievement_id"], row["unlocked_at"])

    return profile_id
