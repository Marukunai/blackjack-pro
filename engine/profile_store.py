# engine/profile_store.py
# Persistencia de perfiles locales en SQLite (saves/profiles.db).
#
# Sustituye al antiguo saves/profile.json de un único perfil: ahora cada
# perfil (nombre + avatar, SIN contraseña — es un juego local de un solo
# jugador, no hay nada que proteger) tiene su propia fila de fichas y
# estadísticas acumuladas, más un historial COMPLETO de manos jugadas en
# la tabla hand_history — antes solo se guardaba el resumen actual, que
# se sobrescribía en cada partida.
# -------------------------------------------------------------
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Optional

from config import i18n


class ProfileStore:
    """Acceso a la base de datos de perfiles locales."""

    DB_PATH = Path("saves/profiles.db")
    LEGACY_JSON_PATH = Path("saves/profile.json")

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path or self.DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._init_schema()
        self._migrate_legacy_json()

    # ------------------------------------------------------------------
    # Esquema y migración
    # ------------------------------------------------------------------
    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS profiles (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                name              TEXT UNIQUE NOT NULL,
                avatar_shape      TEXT NOT NULL DEFAULT 'S',
                avatar_color      TEXT NOT NULL DEFAULT '212,175,55',
                chips             REAL NOT NULL DEFAULT 1000,
                hands_played      INTEGER NOT NULL DEFAULT 0,
                hands_won         INTEGER NOT NULL DEFAULT 0,
                hands_lost        INTEGER NOT NULL DEFAULT 0,
                hands_push        INTEGER NOT NULL DEFAULT 0,
                hands_surrendered INTEGER NOT NULL DEFAULT 0,
                blackjacks        INTEGER NOT NULL DEFAULT 0,
                busts             INTEGER NOT NULL DEFAULT 0,
                total_wagered     REAL NOT NULL DEFAULT 0,
                net_profit        REAL NOT NULL DEFAULT 0,
                peak_chips        REAL NOT NULL DEFAULT 0,
                lowest_chips      REAL NOT NULL DEFAULT 0,
                best_streak       INTEGER NOT NULL DEFAULT 0,
                worst_streak      INTEGER NOT NULL DEFAULT 0,
                hands_split       INTEGER NOT NULL DEFAULT 0,
                created_at        REAL NOT NULL,
                last_played_at    REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS hand_history (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id   INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
                played_at    REAL NOT NULL,
                preset_name  TEXT,
                bet          REAL NOT NULL,
                result       TEXT NOT NULL,
                net          REAL NOT NULL,
                chips_after  REAL NOT NULL,
                replay_data  TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_history_profile
                ON hand_history(profile_id, played_at);

            CREATE TABLE IF NOT EXISTS achievements (
                profile_id      INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
                achievement_id  TEXT NOT NULL,
                unlocked_at     REAL NOT NULL,
                PRIMARY KEY (profile_id, achievement_id)
            );
            """
        )
        self._conn.commit()
        self._migrate_columns()

    def _migrate_columns(self) -> None:
        """Añade columnas nuevas a bases de datos ya existentes (creadas por
        una versión anterior de la app, antes de que existiera esa
        columna). CREATE TABLE IF NOT EXISTS no toca las tablas que ya
        existen, así que las columnas añadidas en versiones posteriores
        necesitan este paso aparte — aditivo y seguro, no toca filas."""
        cols = {row[1] for row in self._conn.execute("PRAGMA table_info(profiles)")}
        if "hands_split" not in cols:
            self._conn.execute(
                "ALTER TABLE profiles ADD COLUMN hands_split INTEGER NOT NULL DEFAULT 0"
            )
            self._conn.commit()

        hh_cols = {row[1] for row in self._conn.execute("PRAGMA table_info(hand_history)")}
        if "replay_data" not in hh_cols:
            self._conn.execute("ALTER TABLE hand_history ADD COLUMN replay_data TEXT")
            self._conn.commit()

    def _migrate_legacy_json(self) -> None:
        """Si existe el antiguo saves/profile.json (perfil único) y todavía
        no hay ningún perfil en la base de datos, lo importa como el primer
        perfil para no perder el progreso ya jugado."""
        if not self.LEGACY_JSON_PATH.exists():
            return
        if self._conn.execute("SELECT COUNT(*) FROM profiles").fetchone()[0] > 0:
            return
        try:
            with open(self.LEGACY_JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return

        name = (data.get("name") or "Jugador").strip() or "Jugador"
        now = time.time()
        chips = data.get("chips", 1000.0)
        try:
            self._conn.execute(
                """INSERT INTO profiles
                   (name, avatar_shape, avatar_color, chips, hands_played, hands_won,
                    hands_lost, hands_push, hands_surrendered, blackjacks, busts,
                    total_wagered, net_profit, peak_chips, lowest_chips, best_streak,
                    worst_streak, created_at, last_played_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    name, "S", "212,175,55",
                    chips,
                    data.get("hands_played", 0),
                    data.get("hands_won", 0),
                    data.get("hands_lost", 0),
                    data.get("hands_push", 0),
                    data.get("hands_surrendered", 0),
                    data.get("blackjacks", 0),
                    data.get("busts", 0),
                    data.get("total_wagered", 0.0),
                    data.get("net_profit", 0.0),
                    data.get("peak_chips", chips),
                    data.get("lowest_chips", chips),
                    data.get("best_streak", 0),
                    data.get("worst_streak", 0),
                    now, now,
                ),
            )
            self._conn.commit()
        except sqlite3.IntegrityError:
            return

        # Renombra el JSON viejo para dejar constancia de que ya se migró
        # (la comprobación de más arriba ya evita re-importarlo, pero así
        # queda claro para quien mire la carpeta de guardado).
        try:
            self.LEGACY_JSON_PATH.rename(self.LEGACY_JSON_PATH.with_suffix(".json.migrated"))
        except OSError:
            pass

    # ------------------------------------------------------------------
    # Perfiles
    # ------------------------------------------------------------------
    def list_profiles(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM profiles ORDER BY last_played_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def create_profile(self, name: str, avatar_shape: str, avatar_color: tuple,
                        starting_chips: float = 1000.0) -> int:
        name = name.strip()
        if not name:
            raise ValueError(i18n.t("profile_store.empty_name"))
        now = time.time()
        color_str = f"{avatar_color[0]},{avatar_color[1]},{avatar_color[2]}"
        try:
            cur = self._conn.execute(
                """INSERT INTO profiles
                   (name, avatar_shape, avatar_color, chips, peak_chips, lowest_chips,
                    created_at, last_played_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (name, avatar_shape, color_str, starting_chips, starting_chips,
                 starting_chips, now, now),
            )
            self._conn.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            raise ValueError(i18n.t("profile_store.duplicate_name", name=name))

    def delete_profile(self, profile_id: int) -> None:
        self._conn.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
        self._conn.commit()

    def get_profile(self, profile_id: int) -> Optional[dict]:
        row = self._conn.execute(
            "SELECT * FROM profiles WHERE id = ?", (profile_id,)
        ).fetchone()
        return dict(row) if row else None

    def touch(self, profile_id: int) -> None:
        self._conn.execute(
            "UPDATE profiles SET last_played_at = ? WHERE id = ?",
            (time.time(), profile_id),
        )
        self._conn.commit()

    def save_stats(self, profile_id: int, fields: dict) -> None:
        """Actualiza fichas y estadísticas acumuladas de un perfil."""
        fields = dict(fields)
        fields["last_played_at"] = time.time()
        cols = ", ".join(f"{k} = ?" for k in fields)
        self._conn.execute(
            f"UPDATE profiles SET {cols} WHERE id = ?",
            (*fields.values(), profile_id),
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Historial de manos (no se sobrescribe nunca, a diferencia del resumen)
    # ------------------------------------------------------------------
    def log_hand(self, profile_id: int, preset_name: str, bet: float,
                 result: str, net: float, chips_after: float,
                 replay_data: Optional[str] = None) -> None:
        self._conn.execute(
            """INSERT INTO hand_history
               (profile_id, played_at, preset_name, bet, result, net, chips_after, replay_data)
               VALUES (?,?,?,?,?,?,?,?)""",
            (profile_id, time.time(), preset_name, bet, result, net, chips_after, replay_data),
        )
        self._conn.commit()

    def get_history(self, profile_id: int, limit: int = 100, offset: int = 0) -> list[dict]:
        rows = self._conn.execute(
            """SELECT * FROM hand_history WHERE profile_id = ?
               ORDER BY played_at DESC LIMIT ? OFFSET ?""",
            (profile_id, limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_all_history(self, profile_id: int) -> list[dict]:
        """Todo el historial de un perfil, sin paginar y en orden
        cronológico ascendente (a diferencia de get_history, pensado para
        la tabla paginada de la UI, que va más reciente primero). Usado
        por engine/csv_export.py (Fase 29) -- un archivo CSV se lee de
        arriba abajo como un registro, no como una tabla que se hojea."""
        rows = self._conn.execute(
            """SELECT * FROM hand_history WHERE profile_id = ?
               ORDER BY played_at ASC""",
            (profile_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def count_history(self, profile_id: int) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) FROM hand_history WHERE profile_id = ?",
            (profile_id,),
        ).fetchone()
        return row[0] if row else 0

    def get_chip_curve(self, profile_id: int, limit: int = 300) -> list[float]:
        """Fichas tras cada una de las últimas `limit` manos, en orden
        cronológico (más antigua primero) -- pensado para dibujar una
        gráfica simple de evolución, no para paginar como get_history."""
        rows = self._conn.execute(
            """SELECT chips_after FROM hand_history WHERE profile_id = ?
               ORDER BY played_at DESC LIMIT ?""",
            (profile_id, limit),
        ).fetchall()
        return [r[0] for r in reversed(rows)]

    # ------------------------------------------------------------------
    # Logros
    # ------------------------------------------------------------------
    def get_unlocked_achievement_ids(self, profile_id: int) -> set[str]:
        rows = self._conn.execute(
            "SELECT achievement_id FROM achievements WHERE profile_id = ?",
            (profile_id,),
        ).fetchall()
        return {r[0] for r in rows}

    def unlock_achievement(self, profile_id: int, achievement_id: str) -> bool:
        """Registra un logro como desbloqueado. Devuelve True si es la
        primera vez (se acaba de insertar), False si ya lo tenía."""
        cur = self._conn.execute(
            """INSERT OR IGNORE INTO achievements (profile_id, achievement_id, unlocked_at)
               VALUES (?, ?, ?)""",
            (profile_id, achievement_id, time.time()),
        )
        self._conn.commit()
        return cur.rowcount > 0

    def close(self) -> None:
        self._conn.close()


# ----------------------------------------------------------------------
# Acceso compartido (una sola conexión SQLite para todo el proceso)
# ----------------------------------------------------------------------
_store: Optional[ProfileStore] = None


def get_store() -> ProfileStore:
    global _store
    if _store is None:
        _store = ProfileStore()
    return _store
