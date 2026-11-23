# tests/test_advanced_stats.py
# Cobertura de la Fase 42 (estadisticas avanzadas: varianza/drawdown y
# desglose de rentabilidad por apuesta lateral; resultados de Torneo
# persistidos en el historial) -- nada de esto tenia test permanente
# antes de esta fase.
from __future__ import annotations

import pytest

from core.player import Player
from engine import profile_store as profile_store_module
from engine.profile_store import ProfileStore
from engine.statistics import StatisticsManager, compute_risk_metrics
from engine.side_bets import SideBetOutcome


@pytest.fixture
def store(tmp_path, monkeypatch):
    instance = ProfileStore(db_path=tmp_path / "advanced_stats.db")
    monkeypatch.setattr(profile_store_module, "_store", instance)
    return instance


class TestSideBetHistory:
    def test_log_and_breakdown_single_kind(self, store):
        pid = store.create_profile("Maruku", "S", (212, 175, 55))
        store.log_side_bet(pid, "perfect_pairs", bet=10.0, net=-10.0, won=False)
        store.log_side_bet(pid, "perfect_pairs", bet=10.0, net=60.0, won=True)
        breakdown = store.get_side_bet_breakdown(pid)
        assert breakdown["perfect_pairs"]["count"] == 2
        assert breakdown["perfect_pairs"]["wagered"] == 20.0
        assert breakdown["perfect_pairs"]["hits"] == 1
        assert breakdown["perfect_pairs"]["net"] == 50.0

    def test_breakdown_separates_by_kind(self, store):
        pid = store.create_profile("Maruku", "S", (212, 175, 55))
        store.log_side_bet(pid, "perfect_pairs", bet=10.0, net=-10.0, won=False)
        store.log_side_bet(pid, "royal_match", bet=5.0, net=20.0, won=True)
        breakdown = store.get_side_bet_breakdown(pid)
        assert set(breakdown.keys()) == {"perfect_pairs", "royal_match"}
        assert breakdown["royal_match"]["net"] == 20.0

    def test_no_side_bets_returns_empty_dict(self, store):
        pid = store.create_profile("Maruku", "S", (212, 175, 55))
        assert store.get_side_bet_breakdown(pid) == {}

    def test_different_profiles_do_not_mix(self, store):
        p1 = store.create_profile("Uno", "S", (212, 175, 55))
        p2 = store.create_profile("Dos", "S", (212, 175, 55))
        store.log_side_bet(p1, "21+3", bet=10.0, net=40.0, won=True)
        assert store.get_side_bet_breakdown(p2) == {}
        assert store.get_side_bet_breakdown(p1)["21+3"]["net"] == 40.0


class TestStatisticsManagerLogSideBets:
    def test_writes_one_row_per_outcome(self, store):
        pid = store.create_profile("Maruku", "S", (212, 175, 55))
        player = Player(chips=1000.0)
        mgr = StatisticsManager(player, profile_id=pid)
        outcomes = [
            SideBetOutcome("perfect_pairs", "Pareja mixta", 6.0, 10.0, 60.0, 70.0),
            SideBetOutcome("21+3", "Sin premio", 0.0, 5.0, -5.0, 0.0),
        ]
        mgr.log_side_bets(outcomes)
        breakdown = store.get_side_bet_breakdown(pid)
        assert breakdown["perfect_pairs"]["hits"] == 1
        assert breakdown["21+3"]["hits"] == 0

    def test_no_profile_id_is_a_noop(self, store):
        player = Player(chips=1000.0)
        mgr = StatisticsManager(player, profile_id=None)
        outcomes = [SideBetOutcome("perfect_pairs", "Pareja mixta", 6.0, 10.0, 60.0, 70.0)]
        mgr.log_side_bets(outcomes)  # no debe lanzar, simplemente no hace nada
        pid = store.create_profile("Maruku", "S", (212, 175, 55))
        assert store.get_side_bet_breakdown(pid) == {}


class TestTournamentResults:
    def test_log_and_get_results(self, store):
        pid = store.create_profile("Maruku", "S", (212, 175, 55))
        store.log_tournament_result(pid, "torneo_rapido", "Torneo Rápido",
                                     rank=1, seats=3, final_chips=1500.0)
        results = store.get_tournament_results(pid)
        assert len(results) == 1
        assert results[0]["rank"] == 1
        assert results[0]["tournament_name"] == "Torneo Rápido"

    def test_summary_counts_wins_and_best_rank(self, store):
        pid = store.create_profile("Maruku", "S", (212, 175, 55))
        store.log_tournament_result(pid, "torneo_rapido", "Torneo Rápido",
                                     rank=2, seats=3, final_chips=900.0)
        store.log_tournament_result(pid, "torneo_estandar", "Torneo Estándar",
                                     rank=1, seats=2, final_chips=1800.0)
        summary = store.get_tournament_summary(pid)
        assert summary["played"] == 2
        assert summary["wins"] == 1
        assert summary["best_rank"] == 1

    def test_summary_with_no_tournaments_played(self, store):
        pid = store.create_profile("Maruku", "S", (212, 175, 55))
        summary = store.get_tournament_summary(pid)
        assert summary == {"played": 0, "wins": 0, "best_rank": None}


class TestComputeRiskMetrics:
    def test_fewer_than_two_hands_returns_zeros(self, store):
        pid = store.create_profile("Maruku", "S", (212, 175, 55))
        store.log_hand(pid, preset_name="Vegas Strip", bet=10.0, result="WIN",
                        net=10.0, chips_after=1010.0)
        metrics = compute_risk_metrics(pid)
        assert metrics == {"hands": 1, "net_stddev": 0.0, "max_drawdown": 0.0, "max_drawdown_pct": 0.0}

    def test_stddev_of_known_sequence(self, store):
        """Nets -10, +10, -10, +10 -> media 0, varianza 100, stddev 10."""
        pid = store.create_profile("Maruku", "S", (212, 175, 55))
        chips = 1000.0
        for net in (-10.0, 10.0, -10.0, 10.0):
            chips += net
            store.log_hand(pid, preset_name="Vegas Strip", bet=10.0,
                            result="WIN" if net > 0 else "LOSS",
                            net=net, chips_after=chips)
        metrics = compute_risk_metrics(pid)
        assert metrics["hands"] == 4
        assert metrics["net_stddev"] == pytest.approx(10.0)

    def test_max_drawdown_from_peak_to_trough(self, store):
        """Curva de fichas 1000 -> 1200 (pico) -> 900 (caida de 300
        desde el pico) -> 1100: el drawdown maximo es 300, no 100
        (1200-1100), ni se confunde con el minimo absoluto de la sesion
        si este fuera anterior al pico."""
        pid = store.create_profile("Maruku", "S", (212, 175, 55))
        curve = [1000.0, 1200.0, 900.0, 1100.0]
        prev = 1000.0
        for chips in curve:
            net = chips - prev
            store.log_hand(pid, preset_name="Vegas Strip", bet=10.0,
                            result="WIN" if net >= 0 else "LOSS",
                            net=net, chips_after=chips)
            prev = chips
        metrics = compute_risk_metrics(pid)
        assert metrics["max_drawdown"] == pytest.approx(300.0)
        assert metrics["max_drawdown_pct"] == pytest.approx(300.0 / 1200.0)

    def test_different_profiles_do_not_mix(self, store):
        p1 = store.create_profile("Uno", "S", (212, 175, 55))
        p2 = store.create_profile("Dos", "S", (212, 175, 55))
        store.log_hand(p1, preset_name="Vegas Strip", bet=10.0, result="WIN",
                        net=10.0, chips_after=1010.0)
        store.log_hand(p1, preset_name="Vegas Strip", bet=10.0, result="LOSS",
                        net=-10.0, chips_after=1000.0)
        assert compute_risk_metrics(p2) == {
            "hands": 0, "net_stddev": 0.0, "max_drawdown": 0.0, "max_drawdown_pct": 0.0,
        }


class TestGetChipCurveUnlimited:
    def test_limit_none_returns_full_history(self, store):
        pid = store.create_profile("Maruku", "S", (212, 175, 55))
        chips = 1000.0
        for _ in range(5):
            chips += 10.0
            store.log_hand(pid, preset_name="Vegas Strip", bet=10.0, result="WIN",
                            net=10.0, chips_after=chips)
        full = store.get_chip_curve(pid, limit=None)
        limited = store.get_chip_curve(pid, limit=2)
        assert len(full) == 5
        assert len(limited) == 2
        assert full[-2:] == limited


class TestGameEnginePersistsSideBetsAutomatically:
    """Verifica el enganche real en GameEngine._resolve_side_bets() (no
    solo StatisticsManager.log_side_bets() en aislamiento): una apuesta
    lateral colocada en una partida con perfil debe acabar en el
    historial sin que nadie llame a nada mas."""

    def test_side_bet_ends_up_in_history(self, store):
        from config.rules_presets import vegas_strip
        from engine.game_engine import GameEngine

        pid = store.create_profile("Maruku", "S", (212, 175, 55))
        rules = vegas_strip()
        rules.perfect_pairs_allowed = True
        rules.side_bet_max = 100.0

        engine = GameEngine(rules=rules, player_name="Maruku", profile_id=pid)
        engine.start_game()
        engine.place_bet(25.0, perfect_pairs=10.0)

        breakdown = store.get_side_bet_breakdown(pid)
        assert "perfect_pairs" in breakdown
        assert breakdown["perfect_pairs"]["count"] == 1
        assert breakdown["perfect_pairs"]["wagered"] == 10.0
