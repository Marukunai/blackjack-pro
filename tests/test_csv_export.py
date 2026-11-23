# tests/test_csv_export.py
# Cobertura de engine/csv_export.py (Fase 29) -- la exportacion a CSV
# solo se habia probado a mano durante esa sesion, nunca con un test
# permanente. Usa una ProfileStore con una base de datos SQLite temporal
# (tmp_path de pytest), nunca saves/profiles.db real.
from __future__ import annotations

import csv

import pytest

from engine import profile_store as profile_store_module
from engine.profile_store import ProfileStore
from engine.csv_export import export_profile_csv, ExportError


@pytest.fixture
def store(tmp_path, monkeypatch):
    """export_profile_csv() usa el ProfileStore global de get_store()
    (una unica conexion SQLite para todo el proceso) -- para que el test
    nunca toque saves/profiles.db real, se sustituye ese singleton por
    uno con una base de datos temporal antes de cada test."""
    instance = ProfileStore(db_path=tmp_path / "profiles.db")
    monkeypatch.setattr(profile_store_module, "_store", instance)
    return instance


@pytest.fixture
def profile_id(store):
    return store.create_profile("Maruku", "S", (212, 175, 55), starting_chips=1000.0)


class TestExportErrors:
    def test_unknown_profile_raises(self, store, tmp_path):
        with pytest.raises(ExportError):
            export_profile_csv(999, out_dir=tmp_path / "out")

    def test_profile_without_hands_raises(self, store, profile_id, tmp_path):
        with pytest.raises(ExportError):
            export_profile_csv(profile_id, out_dir=tmp_path / "out")


class TestExportContent:
    def _log_sample_hands(self, store, profile_id):
        store.log_hand(profile_id, "vegas_strip", 25.0, "WIN", 25.0, 1025.0)
        store.log_hand(profile_id, "vegas_strip", 25.0, "LOSS", -25.0, 1000.0)
        store.log_hand(profile_id, "european", 50.0, "BLACKJACK_WIN", 75.0, 1075.0)
        store.save_stats(profile_id, {
            "chips": 1075.0, "hands_played": 3, "hands_won": 2, "hands_lost": 1,
            "total_wagered": 100.0, "net_profit": 75.0, "peak_chips": 1075.0,
            "lowest_chips": 1000.0,
        })

    def test_creates_a_csv_file(self, store, profile_id, tmp_path):
        self._log_sample_hands(store, profile_id)
        out_dir = tmp_path / "out"
        path = export_profile_csv(profile_id, out_dir=out_dir)
        assert path.exists()
        assert path.suffix == ".csv"
        assert path.parent == out_dir

    def test_filename_contains_profile_name(self, store, profile_id, tmp_path):
        self._log_sample_hands(store, profile_id)
        path = export_profile_csv(profile_id, out_dir=tmp_path / "out")
        assert "Maruku" in path.name

    def test_summary_block_has_the_right_numbers(self, store, profile_id, tmp_path):
        self._log_sample_hands(store, profile_id)
        path = export_profile_csv(profile_id, out_dir=tmp_path / "out")
        with open(path, newline="", encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))
        summary = {row[0]: row[1] for row in rows if len(row) == 2}
        assert summary["Perfil"] == "Maruku"
        assert summary["Manos jugadas"] == "3"
        assert summary["Victorias"] == "2"

    def test_hand_table_has_one_row_per_logged_hand(self, store, profile_id, tmp_path):
        self._log_sample_hands(store, profile_id)
        path = export_profile_csv(profile_id, out_dir=tmp_path / "out")
        with open(path, newline="", encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))
        # La fila de cabecera de la tabla de manos es la unica con
        # exactamente 6 columnas y que no es puramente numerica.
        header_idx = next(i for i, r in enumerate(rows) if r and r[0] == "Fecha")
        hand_rows = rows[header_idx + 1:]
        assert len(hand_rows) == 3

    def test_hand_results_are_translated_not_raw_keys(self, store, profile_id, tmp_path):
        """Mismo tipo de bug que el corregido en hand_replay.py durante
        esta misma fase: el CSV no debe mostrar 'WIN' o 'BLACKJACK_WIN'
        en crudo, sino la etiqueta traducida."""
        self._log_sample_hands(store, profile_id)
        path = export_profile_csv(profile_id, out_dir=tmp_path / "out")
        content = path.read_text(encoding="utf-8-sig")
        assert "BLACKJACK_WIN" not in content
        assert "Blackjack" in content or "blackjack" in content.lower()

    def test_utf8_bom_for_excel(self, store, profile_id, tmp_path):
        self._log_sample_hands(store, profile_id)
        path = export_profile_csv(profile_id, out_dir=tmp_path / "out")
        raw = path.read_bytes()
        assert raw.startswith(b"\xef\xbb\xbf")
