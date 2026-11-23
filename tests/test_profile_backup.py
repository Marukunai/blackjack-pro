# tests/test_profile_backup.py
# Cobertura de engine/profile_backup.py (Fase 32): copia de seguridad y
# restauración de un perfil completo (fichas + estadísticas + historial
# + logros) a un archivo JSON, como complemento de la exportación a CSV
# de la Fase 29 (esa es de solo lectura; esta es de ida y vuelta).
from __future__ import annotations

import pytest

from engine import profile_store as profile_store_module
from engine.profile_store import ProfileStore
from engine.profile_backup import (
    export_profile_backup,
    import_profile_backup,
    preview_profile_backup,
    BackupError,
)


@pytest.fixture
def store_a(tmp_path, monkeypatch):
    """El perfil "de origen", simulando el equipo donde se exporta."""
    instance = ProfileStore(db_path=tmp_path / "a.db")
    monkeypatch.setattr(profile_store_module, "_store", instance)
    return instance


def _use_store(monkeypatch, instance):
    monkeypatch.setattr(profile_store_module, "_store", instance)
    return instance


@pytest.fixture
def profile_id(store_a):
    pid = store_a.create_profile("Maruku", "S", (212, 175, 55), starting_chips=1000.0)
    store_a.log_hand(pid, "vegas_strip", 25.0, "WIN", 25.0, 1025.0, replay_data='{"x":1}')
    store_a.log_hand(pid, "european", 50.0, "LOSS", -50.0, 975.0)
    store_a.save_stats(pid, {
        "chips": 975.0, "hands_played": 2, "hands_won": 1, "hands_lost": 1,
        "peak_chips": 1025.0, "lowest_chips": 975.0,
    })
    store_a.unlock_achievement(pid, "first_win")
    return pid


class TestExport:
    def test_unknown_profile_raises(self, store_a, tmp_path):
        with pytest.raises(BackupError):
            export_profile_backup(999, out_dir=tmp_path / "out")

    def test_creates_a_json_file(self, store_a, profile_id, tmp_path):
        path = export_profile_backup(profile_id, out_dir=tmp_path / "out")
        assert path.exists()
        assert path.suffix == ".json"

    def test_preview_matches_the_exported_profile(self, store_a, profile_id, tmp_path):
        path = export_profile_backup(profile_id, out_dir=tmp_path / "out")
        preview = preview_profile_backup(path)
        assert preview["name"] == "Maruku"
        assert preview["chips"] == 975.0
        assert preview["hand_count"] == 2
        assert preview["achievement_count"] == 1


class TestImportRoundTrip:
    """El caso de uso real: exportar en un equipo, importar en otro (o
    en una instalación nueva) -- se simula con dos ProfileStore
    distintos, nunca reimportando sobre el mismo perfil de origen."""

    def test_round_trip_preserves_chips_and_stats(self, store_a, profile_id, tmp_path, monkeypatch):
        path = export_profile_backup(profile_id, out_dir=tmp_path / "out")
        store_b = ProfileStore(db_path=tmp_path / "b.db")
        _use_store(monkeypatch, store_b)

        new_pid = import_profile_backup(path)
        restored = store_b.get_profile(new_pid)
        assert restored["name"] == "Maruku"
        assert restored["chips"] == 975.0
        assert restored["hands_played"] == 2
        assert restored["hands_won"] == 1
        assert restored["peak_chips"] == 1025.0

    def test_round_trip_preserves_hand_history_with_original_dates(
        self, store_a, profile_id, tmp_path, monkeypatch
    ):
        original_history = store_a.get_all_history(profile_id)
        path = export_profile_backup(profile_id, out_dir=tmp_path / "out")
        store_b = ProfileStore(db_path=tmp_path / "b.db")
        _use_store(monkeypatch, store_b)

        new_pid = import_profile_backup(path)
        restored_history = store_b.get_all_history(new_pid)
        assert len(restored_history) == len(original_history)
        for original, restored in zip(original_history, restored_history):
            assert restored["played_at"] == original["played_at"]
            assert restored["result"] == original["result"]
            assert restored["net"] == original["net"]
        assert restored_history[0]["replay_data"] == '{"x":1}'

    def test_round_trip_preserves_achievements(self, store_a, profile_id, tmp_path, monkeypatch):
        path = export_profile_backup(profile_id, out_dir=tmp_path / "out")
        store_b = ProfileStore(db_path=tmp_path / "b.db")
        _use_store(monkeypatch, store_b)

        new_pid = import_profile_backup(path)
        assert store_b.get_unlocked_achievement_ids(new_pid) == {"first_win"}

    def test_import_creates_a_new_profile_never_overwrites(
        self, store_a, profile_id, tmp_path, monkeypatch
    ):
        path = export_profile_backup(profile_id, out_dir=tmp_path / "out")
        store_b = ProfileStore(db_path=tmp_path / "b.db")
        _use_store(monkeypatch, store_b)
        other_pid = store_b.create_profile("Alguien", "C", (100, 100, 100))

        new_pid = import_profile_backup(path)
        assert new_pid != other_pid
        assert store_b.get_profile(other_pid) is not None   # no se tocó


class TestImportErrors:
    def test_duplicate_name_in_destination_raises(self, store_a, profile_id, tmp_path):
        """Importar sobre el MISMO store donde ya existe un perfil con
        ese nombre debe fallar con un mensaje claro, no sobrescribir."""
        path = export_profile_backup(profile_id, out_dir=tmp_path / "out")
        with pytest.raises(BackupError):
            import_profile_backup(path)   # "Maruku" ya existe en store_a

    def test_explicit_new_name_avoids_the_collision(self, store_a, profile_id, tmp_path):
        path = export_profile_backup(profile_id, out_dir=tmp_path / "out")
        new_pid = import_profile_backup(path, new_name="Maruku (copia)")
        assert store_a.get_profile(new_pid)["name"] == "Maruku (copia)"

    def test_corrupted_file_raises_backup_error_not_a_crash(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("esto no es json", encoding="utf-8")
        with pytest.raises(BackupError):
            import_profile_backup(bad)

    def test_file_with_wrong_shape_raises(self, tmp_path):
        import json
        bad = tmp_path / "wrong_shape.json"
        bad.write_text(json.dumps({"hola": "mundo"}), encoding="utf-8")
        with pytest.raises(BackupError):
            import_profile_backup(bad)

    def test_future_backup_format_is_rejected(self, tmp_path):
        import json
        future = tmp_path / "future.json"
        future.write_text(json.dumps({
            "backup_format": 999, "profile": {"name": "X", "chips": 100.0},
            "hand_history": [], "achievements": [],
        }), encoding="utf-8")
        with pytest.raises(BackupError):
            import_profile_backup(future)
