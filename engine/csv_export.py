# engine/csv_export.py
# Exportación del historial de manos y las estadísticas acumuladas de un
# perfil a un archivo CSV (Fase 29), a petición de Maruku.
#
# Un único archivo por exportación, pensado para abrirse en Excel/Sheets:
# primero un bloque de resumen (las mismas cifras que ya se ven en el
# panel de estadísticas F3 y en StatisticsManager.summary(), pero
# traducidas al idioma activo), una línea en blanco, y después la tabla
# completa de manos jugadas en orden cronológico (todas, no solo la
# página que se esté viendo en HandHistoryScreen). Un CSV admite filas de
# distinta longitud sin problema -- no hace falta que el bloque de
# resumen tenga las mismas columnas que la tabla de manos.
# -------------------------------------------------------------
from __future__ import annotations

import csv
import re
import time
from pathlib import Path
from typing import Optional

from config import settings as cfg
from config import i18n
from engine.profile_store import get_store

EXPORTS_DIR = cfg.SAVES_DIR / "exports"

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9 _-]+")


class ExportError(Exception):
    """Fallo al exportar (perfil inexistente, error de E/S, etc.)."""


def _safe_filename_part(name: str) -> str:
    """Convierte el nombre de perfil en algo seguro para un nombre de
    archivo en Windows/macOS/Linux (sin barras, dos puntos, etc.)."""
    cleaned = _SAFE_NAME_RE.sub("_", name).strip("_ ")
    return cleaned or "jugador"


def _fmt_date(ts: float) -> str:
    try:
        return time.strftime("%d/%m/%Y %H:%M", time.localtime(ts))
    except (OSError, ValueError):
        return "—"


def export_profile_csv(profile_id: int, out_dir: Optional[Path] = None) -> Path:
    """Exporta el resumen de estadísticas + historial completo de manos
    del perfil dado a un nuevo archivo CSV en `out_dir` (por defecto
    saves/exports/, junto a profiles.db). Devuelve la ruta del archivo
    creado. Lanza ExportError si el perfil no existe o no hay ninguna
    mano registrada (nada útil que exportar)."""
    store = get_store()
    profile = store.get_profile(profile_id)
    if profile is None:
        raise ExportError(f"profile_id {profile_id} no existe")

    rows = store.get_all_history(profile_id)
    if not rows:
        raise ExportError("sin manos registradas")

    target_dir = out_dir or EXPORTS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    stamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"blackjack_{_safe_filename_part(profile['name'])}_{stamp}.csv"
    path = target_dir / filename

    hands_played = profile.get("hands_played", 0)
    win_rate = (profile.get("hands_won", 0) / hands_played) if hands_played else 0.0

    # utf-8-sig (con BOM) para que Excel en Windows detecte UTF-8 solo y
    # muestre bien los acentos/eñes de es/fr/pt/de -- sin el BOM, Excel
    # (no LibreOffice) suele interpretarlo como Latin-1 y rompe los tildes.
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)

        w.writerow([i18n.t("csv.summary_title")])
        w.writerow([i18n.t("csv.label_profile"), profile["name"]])
        w.writerow([i18n.t("csv.label_generated"), _fmt_date(time.time())])
        w.writerow([i18n.t("csv.label_current_chips"), f"{profile.get('chips', 0.0):.2f}"])
        w.writerow([i18n.t("csv.label_hands_played"), hands_played])
        w.writerow([i18n.t("csv.label_hands_won"), profile.get("hands_won", 0)])
        w.writerow([i18n.t("csv.label_hands_lost"), profile.get("hands_lost", 0)])
        w.writerow([i18n.t("csv.label_hands_push"), profile.get("hands_push", 0)])
        w.writerow([i18n.t("csv.label_hands_surrendered"), profile.get("hands_surrendered", 0)])
        w.writerow([i18n.t("csv.label_blackjacks"), profile.get("blackjacks", 0)])
        w.writerow([i18n.t("csv.label_busts"), profile.get("busts", 0)])
        w.writerow([i18n.t("csv.label_hands_split"), profile.get("hands_split", 0)])
        w.writerow([i18n.t("csv.label_win_rate"), f"{win_rate:.1%}"])
        w.writerow([i18n.t("csv.label_total_wagered"), f"{profile.get('total_wagered', 0.0):.2f}"])
        w.writerow([i18n.t("csv.label_net_profit"), f"{profile.get('net_profit', 0.0):+.2f}"])
        w.writerow([i18n.t("csv.label_best_streak"), profile.get("best_streak", 0)])
        w.writerow([i18n.t("csv.label_worst_streak"), profile.get("worst_streak", 0)])
        w.writerow([i18n.t("csv.label_peak_chips"), f"{profile.get('peak_chips', 0.0):.2f}"])
        w.writerow([i18n.t("csv.label_lowest_chips"), f"{profile.get('lowest_chips', 0.0):.2f}"])
        w.writerow([])

        w.writerow([
            i18n.t("history.col_date"), i18n.t("history.col_casino"),
            i18n.t("history.col_bet"), i18n.t("history.col_result"),
            i18n.t("history.col_net"), i18n.t("history.col_chips"),
        ])
        for row in rows:
            preset_name = row.get("preset_name")
            preset = i18n.preset_label(preset_name) if preset_name else "—"
            w.writerow([
                _fmt_date(row["played_at"]),
                preset,
                f"{row['bet']:.2f}",
                i18n.hand_result_label(row["result"]),
                f"{row['net']:+.2f}",
                f"{row['chips_after']:.2f}",
            ])

    return path
