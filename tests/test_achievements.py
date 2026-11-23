# tests/test_achievements.py
# Cobertura de engine/achievements.py -- antes de esta fase el catalogo de
#21 logros no tenia ningun test permanente: ni que los ids fueran unicos
# ni que las condiciones `check` se dispararan donde deben.
from __future__ import annotations

import pytest

from core.player import Player, SessionStats
from engine.achievements import ACHIEVEMENTS, _comeback, unlock_backup_achievement
from engine import profile_store as profile_store_module
from engine.profile_store import ProfileStore


class TestAchievementCatalog:
    def test_all_ids_are_unique(self):
        ids = [a.id for a in ACHIEVEMENTS]
        assert len(ids) == len(set(ids))

    def test_catalog_is_not_empty(self):
        assert len(ACHIEVEMENTS) >= 20

    def test_every_achievement_has_name_description_icon(self):
        for a in ACHIEVEMENTS:
            assert a.name
            assert a.description
            assert a.icon
            assert isinstance(a.color, tuple) and len(a.color) == 3

    def test_fresh_stats_unlock_nothing(self):
        """Un perfil recien creado, sin manos jugadas, no debe cumplir
        ninguna condicion -- si alguna lo hiciera, se desbloquearia de
        inmediato para todo jugador nuevo."""
        stats = SessionStats()
        player = Player(chips=1000.0)
        for a in ACHIEVEMENTS:
            assert a.check(stats, player) is False, f"{a.id} se dispara sin jugar ninguna mano"


class TestSpecificAchievements:
    def _get(self, achievement_id: str):
        return next(a for a in ACHIEVEMENTS if a.id == achievement_id)

    def test_first_win_unlocks_after_one_win(self):
        stats = SessionStats()
        player = Player(chips=1000.0)
        stats.record_win(10.0)
        assert self._get("first_win").check(stats, player) is True

    def test_streak_5_requires_five_in_a_row(self):
        stats = SessionStats()
        player = Player(chips=1000.0)
        for _ in range(4):
            stats.record_win(10.0)
        assert self._get("streak_5").check(stats, player) is False
        stats.record_win(10.0)
        assert self._get("streak_5").check(stats, player) is True

    def test_high_roller_needs_peak_chips(self):
        stats = SessionStats()
        player = Player(chips=1000.0)
        stats.peak_chips = 4999.0
        assert self._get("high_roller").check(stats, player) is False
        stats.peak_chips = 5000.0
        assert self._get("high_roller").check(stats, player) is True

    def test_first_split_needs_at_least_one_split(self):
        stats = SessionStats()
        player = Player(chips=1000.0)
        assert self._get("first_split").check(stats, player) is False
        stats.hands_split = 1
        assert self._get("first_split").check(stats, player) is True


class TestComebackAchievement:
    """_comeback() es relativo al propio pico del jugador, no a una cifra
    fija -- por eso merece sus propios tests (Fase 24)."""

    def test_no_comeback_without_a_prior_drop(self):
        stats = SessionStats()
        stats.peak_chips = 1000.0
        stats.lowest_chips = 900.0
        player = Player(chips=1000.0)
        assert _comeback(stats, player) is False

    def test_comeback_after_falling_to_15_percent_and_recovering_past_half(self):
        stats = SessionStats()
        stats.peak_chips = 1000.0
        stats.lowest_chips = 100.0   # 10% del pico, por debajo del umbral del 15%
        player = Player(chips=600.0)  # recuperado a más de la mitad del pico
        assert _comeback(stats, player) is True

    def test_no_comeback_if_still_below_half_of_peak(self):
        stats = SessionStats()
        stats.peak_chips = 1000.0
        stats.lowest_chips = 100.0
        player = Player(chips=400.0)   # no ha llegado a la mitad del pico (500)
        assert _comeback(stats, player) is False

    def test_no_comeback_with_no_recorded_peak(self):
        stats = SessionStats()   # peak_chips/lowest_chips en su valor por defecto
        player = Player(chips=1000.0)
        assert _comeback(stats, player) is False


class TestFase37SideBetAndBotAchievements:
    """Logros nuevos ligados a las apuestas laterales de la Fase 31
    (Lucky Ladies, Royal Match) y a los oponentes IA de la Fase 35."""

    def _get(self, achievement_id: str):
        return next(a for a in ACHIEVEMENTS if a.id == achievement_id)

    def test_lucky_lady_requires_at_least_one_win(self):
        stats = SessionStats()
        player = Player(chips=1000.0)
        assert self._get("lucky_lady").check(stats, player) is False
        stats.lucky_ladies_wins = 1
        assert self._get("lucky_lady").check(stats, player) is True

    def test_royal_pair_requires_at_least_one_win(self):
        stats = SessionStats()
        player = Player(chips=1000.0)
        assert self._get("royal_pair").check(stats, player) is False
        stats.royal_match_wins = 1
        assert self._get("royal_pair").check(stats, player) is True

    def test_vs_bots_requires_at_least_one_hand_at_a_bot_table(self):
        stats = SessionStats()
        player = Player(chips=1000.0)
        assert self._get("vs_bots").check(stats, player) is False
        stats.hands_vs_bot = 1
        assert self._get("vs_bots").check(stats, player) is True


class TestBackupAchievement:
    """'backup_used' es un logro "meta": su check() siempre es False (no
    depende de ninguna estadística de partida) -- se desbloquea aparte,
    directamente, desde ui/profile_select.py vía unlock_backup_achievement()
    justo tras exportar/importar una copia de seguridad con éxito."""

    def test_check_never_fires_on_its_own(self):
        stats = SessionStats()
        player = Player(chips=1000.0)
        ach = next(a for a in ACHIEVEMENTS if a.id == "backup_used")
        # ninguna combinación razonable de estadísticas debería dispararlo
        stats.hands_played = 99999
        stats.peak_chips = 999999.0
        assert ach.check(stats, player) is False

    @pytest.fixture
    def store(self, tmp_path, monkeypatch):
        instance = ProfileStore(db_path=tmp_path / "achievements.db")
        monkeypatch.setattr(profile_store_module, "_store", instance)
        return instance

    def test_unlocks_once_and_returns_the_achievement(self, store):
        pid = store.create_profile("Maruku", "S", (212, 175, 55))
        ach = unlock_backup_achievement(pid, store)
        assert ach is not None
        assert ach.id == "backup_used"
        assert "backup_used" in store.get_unlocked_achievement_ids(pid)

    def test_second_call_returns_none_already_unlocked(self, store):
        pid = store.create_profile("Maruku", "S", (212, 175, 55))
        unlock_backup_achievement(pid, store)
        assert unlock_backup_achievement(pid, store) is None

    def test_none_profile_id_returns_none(self, store):
        assert unlock_backup_achievement(None, store) is None
