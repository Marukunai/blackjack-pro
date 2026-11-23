# tests/test_challenges.py
# Cobertura del modo Desafio (engine/challenges.py, Fase 25) -- la logica
# de evaluate()/progress()/build_rules() no tenia ningun test permanente,
# incluida la regla "las fichas iniciales del desafio son siempre las
# suyas, nunca el saldo real del perfil" (fix de la Fase 26/27).
from __future__ import annotations

import pytest

from core.player import SessionStats
from engine.challenges import Challenge, CHALLENGES, get_challenge


def _stats(hands_played=0, current_streak=0, hand_log=None) -> SessionStats:
    s = SessionStats()
    s.hands_played = hands_played
    s.current_streak = current_streak
    if hand_log:
        s.hand_log = hand_log
    return s


class TestChallengeCatalog:
    def test_all_ids_are_unique(self):
        ids = [c.id for c in CHALLENGES]
        assert len(ids) == len(set(ids))

    def test_get_challenge_returns_the_right_one(self):
        c = get_challenge("meta_rapida")
        assert c.name == "Meta Rápida"

    def test_get_unknown_challenge_raises(self):
        with pytest.raises(KeyError):
            get_challenge("no_existe")

    def test_build_rules_always_uses_the_challenge_own_starting_chips(self):
        """Regresion: los Desafios deben empezar siempre con SUS propias
        fichas iniciales, no con el saldo real (potencialmente muy
        distinto) del perfil que los juega."""
        for c in CHALLENGES:
            rules = c.build_rules()
            assert rules.starting_chips == c.starting_chips
            assert rules.min_bet == c.min_bet
            assert rules.max_bet == c.max_bet


class TestTargetChips:
    def test_in_progress_before_reaching_target(self):
        c = get_challenge("meta_rapida")
        stats = _stats(hands_played=5)
        assert c.evaluate(stats, chips=1200.0) == "in_progress"

    def test_won_on_reaching_target_chips(self):
        c = get_challenge("meta_rapida")
        stats = _stats(hands_played=5)
        assert c.evaluate(stats, chips=1500.0) == "won"

    def test_lost_if_hand_limit_reached_without_target(self):
        c = get_challenge("meta_rapida")
        stats = _stats(hands_played=20)
        assert c.evaluate(stats, chips=1200.0) == "lost"


class TestTargetStreak:
    def test_won_on_reaching_streak(self):
        c = get_challenge("racha_hierro")
        stats = _stats(hands_played=3, current_streak=5)
        assert c.evaluate(stats, chips=1100.0) == "won"

    def test_fail_on_any_loss_ends_immediately(self):
        """racha_hierro usa fail_on_any_loss: una sola derrota termina el
        desafio al instante, aunque aun queden manos disponibles."""
        c = get_challenge("racha_hierro")
        stats = _stats(hands_played=2, current_streak=0,
                        hand_log=[("win", 1), ("loss", 0)])
        assert c.evaluate(stats, chips=900.0) == "lost"

    def test_push_does_not_trigger_fail_on_any_loss(self):
        c = get_challenge("racha_hierro")
        stats = _stats(hands_played=2, current_streak=0,
                        hand_log=[("win", 1), ("push", 0)])
        assert c.evaluate(stats, chips=1000.0) == "in_progress"


class TestRequireProfit:
    def test_in_progress_before_hand_limit(self):
        c = get_challenge("contrarreloj")
        stats = _stats(hands_played=10)
        assert c.evaluate(stats, chips=1050.0) == "in_progress"

    def test_won_if_profitable_at_the_limit(self):
        c = get_challenge("contrarreloj")
        stats = _stats(hands_played=15)
        assert c.evaluate(stats, chips=1050.0) == "won"

    def test_lost_if_not_profitable_at_the_limit(self):
        c = get_challenge("contrarreloj")
        stats = _stats(hands_played=15)
        assert c.evaluate(stats, chips=950.0) == "lost"

    def test_exact_break_even_is_not_a_win(self):
        c = get_challenge("contrarreloj")
        stats = _stats(hands_played=15)
        assert c.evaluate(stats, chips=c.starting_chips) == "lost"


class TestSurviveOnly:
    """superviviente no tiene target_chips/target_streak/require_profit:
    llegar vivo al limite de manos ya es la victoria."""

    def test_won_by_surviving_to_the_limit(self):
        c = get_challenge("superviviente")
        stats = _stats(hands_played=25)
        assert c.evaluate(stats, chips=50.0) == "won"

    def test_in_progress_before_the_limit(self):
        c = get_challenge("superviviente")
        stats = _stats(hands_played=10)
        assert c.evaluate(stats, chips=50.0) == "in_progress"


class TestProgress:
    def test_progress_clamped_between_zero_and_one(self):
        c = get_challenge("meta_rapida")
        stats = _stats()
        assert c.progress(stats, chips=0.0) == 0.0
        assert c.progress(stats, chips=999999.0) == 1.0

    def test_progress_label_does_not_crash_for_every_challenge(self):
        for c in CHALLENGES:
            stats = _stats(hands_played=1, current_streak=1)
            label = c.progress_label(stats, chips=c.starting_chips)
            assert isinstance(label, str) and label
