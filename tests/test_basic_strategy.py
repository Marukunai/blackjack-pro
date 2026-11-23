# tests/test_basic_strategy.py
# Cobertura de ai/basic_strategy.py -- en particular el caso de la
# "rendicion fantasma": antes de este test, _resolve_action() solo
# comprobaba rules.surrender_rule para las acciones R/RS/RP, sin tener
# en cuenta que la rendicion SOLO es legal como primerisima decision de
# la mano (2 cartas, sin provenir de un split). Con una mano que ya
# habia pedido carta (p.ej. hard 15 tras un hit), recommended_play()
# podia devolver "surrender" aunque GameEngine.get_available_actions()
# ya no lo ofreciera -- y como el oponente IA (ui/renderer.py,
# _run_bot_turn) ejecuta ciegamente lo que recommended_play() le dice,
# esa accion invalida no hacia nada y dejaba el asiento congelado para
# siempre (bug real, reproducido con una mesa de 3 asientos y apuestas
# laterales activas).
from __future__ import annotations

from ai.basic_strategy import (
    get_basic_strategy, recommended_play, BasicAction,
    apply_personality, recommended_play_with_personality, PERSONALITIES,
)
from core.card import Card
from core.hand import Hand
from core.rules import Rules, SurrenderRule
from engine.actions import available_actions
from core.player import Player
from core.dealer import Dealer


def make_hand(*rank_suit_pairs) -> Hand:
    h = Hand(bet=10)
    for rank, suit in rank_suit_pairs:
        h.add_card(Card(rank, suit))
    return h


class TestSurrenderOnlyAsFirstAction:
    def test_two_card_hard_15_vs_10_recommends_surrender_when_allowed(self):
        rules = Rules()
        rules.surrender_rule = SurrenderRule.LATE
        hand = make_hand(("10", "♣"), ("5", "♦"))   # hard 15, 2 cartas
        assert recommended_play(hand, 10, rules) == "surrender"

    def test_three_card_hard_15_vs_10_never_recommends_surrender(self):
        """Caso real del bug: la misma mano hard 15, pero llegada tras un
        hit (3 cartas) -- la rendicion ya no es una opcion legal, así que
        la recomendación debe caer a "hit" (el "else" de "Surrender, else
        Hit"), nunca a "surrender"."""
        rules = Rules()
        rules.surrender_rule = SurrenderRule.LATE
        hand = make_hand(("2", "♣"), ("3", "♣"), ("10", "♣"))   # hard 15, 3 cartas
        action = recommended_play(hand, 10, rules)
        assert action != "surrender"
        assert action == "hit"

    def test_split_hand_with_two_cards_never_recommends_surrender(self):
        """Una mano con exactamente 2 cartas pero marcada is_split=True
        (viene de un split) tampoco puede rendirse."""
        rules = Rules()
        rules.surrender_rule = SurrenderRule.LATE
        hand = make_hand(("10", "♣"), ("5", "♦"))
        hand.is_split = True
        action = recommended_play(hand, 10, rules)
        assert action != "surrender"

    def test_recommendation_always_matches_a_really_available_action(self):
        """Propiedad general: para cualquier mano no terminada,
        recommended_play() nunca debe sugerir algo que
        GameEngine/available_actions() consideraria invalido ahora mismo
        -- esto es lo que garantiza que un oponente IA que ejecuta la
        recomendacion a ciegas (ui/renderer.py::_run_bot_turn) nunca se
        quede congelado esperando una accion que el motor rechaza."""
        rules = Rules()
        rules.surrender_rule = SurrenderRule.LATE
        dealer = Dealer()
        player = Player(name="Bot")

        scenarios = [
            # (cartas, upcard) -- incluye el caso de la mano de 3 cartas
            # que originaba el atasco real.
            ([("10", "♣"), ("5", "♦")], 10),
            ([("2", "♣"), ("3", "♣"), ("10", "♣")], 10),
            ([("9", "♠"), ("7", "♥")], 10),
            ([("8", "♠"), ("8", "♥")], 10),
            ([("A", "♠"), ("7", "♥")], 2),
        ]
        for cards, upcard_value in scenarios:
            hand = make_hand(*cards)
            player.hands = [hand]
            player.active_hand_index = 0
            is_first = len(hand.cards) == 2 and not hand.is_split
            valid = available_actions(hand, player, dealer, rules, is_first)
            action = recommended_play(hand, upcard_value, rules)
            assert action in valid, (
                f"recommended_play devolvió {action!r} para {hand} "
                f"(is_first={is_first}) pero las acciones válidas son {valid}"
            )


class TestResolveActionFallbacks:
    def test_surrender_disabled_by_rules_falls_back_to_hit(self):
        rules = Rules()
        rules.surrender_rule = SurrenderRule.NONE
        hand = make_hand(("10", "♣"), ("5", "♦"))
        assert get_basic_strategy(hand, 10, rules) == BasicAction.H

    def test_already_surrendered_hand_never_recommends_surrender_again(self):
        rules = Rules()
        rules.surrender_rule = SurrenderRule.LATE
        hand = make_hand(("10", "♣"), ("5", "♦"))
        hand.surrendered = True
        action = recommended_play(hand, 10, rules)
        assert action != "surrender"


class TestBotPersonalities:
    """Fase 38: apply_personality() desvía la recomendación de estrategia
    básica según la 'personalidad' del bot -- nunca debe convertir un
    hit/stand/surrender en otra cosa (solo toca double/split), para que
    la jugada resultante siga siendo razonable y, sobre todo, para que
    nunca recomiende algo que la mano no pueda hacer de verdad."""

    def test_perfect_personality_never_changes_the_action(self):
        rules = Rules()
        hand = make_hand(("8", "♠"), ("8", "♥"))   # par de ochos: Split por tabla
        base = recommended_play(hand, 6, rules)
        assert apply_personality(base, hand, "perfect") == base

    def test_unknown_personality_falls_back_to_the_base_action(self):
        hand = make_hand(("8", "♠"), ("8", "♥"))
        assert apply_personality("split", hand, "not-a-real-personality") == "split"

    def test_conservative_never_doubles(self):
        hand = make_hand(("5", "♠"), ("6", "♥"))   # hard 11, 2 cartas -- can_double
        assert apply_personality("double", hand, "conservative") == "hit"

    def test_conservative_never_splits(self):
        hand = make_hand(("8", "♠"), ("8", "♥"))
        assert apply_personality("split", hand, "conservative") == "hit"

    def test_conservative_leaves_hit_stand_surrender_untouched(self):
        hand = make_hand(("10", "♣"), ("7", "♦"))
        for base in ("hit", "stand", "surrender"):
            assert apply_personality(base, hand, "conservative") == base

    def test_aggressive_splits_any_pair_it_can(self):
        hand = make_hand(("4", "♠"), ("4", "♥"))   # par de cuatros: tabla dice Hit normalmente
        assert apply_personality("hit", hand, "aggressive") == "split"

    def test_aggressive_doubles_hard_9_to_11_on_first_action(self):
        hand = make_hand(("6", "♠"), ("4", "♥"))   # hard 10, 2 cartas, can_double
        assert apply_personality("hit", hand, "aggressive") == "double"

    def test_aggressive_does_not_double_outside_9_to_11(self):
        hand = make_hand(("10", "♣"), ("5", "♦"))   # hard 15
        assert apply_personality("hit", hand, "aggressive") == "hit"

    def test_aggressive_does_not_double_a_three_card_hand(self):
        """Solo puede doblar como primera decisión (2 cartas) -- igual
        que can_double ya exige en core/hand.py."""
        hand = make_hand(("3", "♠"), ("3", "♥"), ("4", "♦"))   # hard 10, 3 cartas
        assert apply_personality("hit", hand, "aggressive") == "hit"

    def test_aggressive_leaves_surrender_untouched(self):
        hand = make_hand(("10", "♣"), ("6", "♦"))
        assert apply_personality("surrender", hand, "aggressive") == "surrender"

    def test_every_personality_always_recommends_a_really_available_action(self):
        """Misma propiedad que ya se exige a recommended_play() a secas
        (ver TestSurrenderOnlyAsFirstAction más arriba), ahora para las
        tres personalidades: nunca debe sugerir algo que el motor
        consideraría inválido ahora mismo -- es justo lo que evita que un
        bot se quede congelado para siempre en mitad de su turno."""
        from engine.actions import available_actions
        from core.player import Player
        from core.dealer import Dealer

        rules = Rules()
        rules.surrender_rule = SurrenderRule.LATE
        dealer = Dealer()
        player = Player(name="Bot")

        scenarios = [
            ([("5", "♠"), ("6", "♥")], 6),           # hard 11, puede doblar
            ([("8", "♠"), ("8", "♥")], 6),           # par de ochos, puede separar
            ([("4", "♠"), ("4", "♥")], 5),           # par de cuatros, puede separar
            ([("2", "♣"), ("3", "♣"), ("10", "♣")], 10),  # 3 cartas, hard 15
            ([("10", "♣"), ("5", "♦")], 10),          # hard 15, 2 cartas, puede rendirse
            ([("A", "♠"), ("7", "♥")], 2),            # soft 18
        ]
        for personality in PERSONALITIES:
            for cards, upcard_value in scenarios:
                hand = make_hand(*cards)
                player.hands = [hand]
                player.active_hand_index = 0
                is_first = len(hand.cards) == 2 and not hand.is_split
                valid = available_actions(hand, player, dealer, rules, is_first)
                action = recommended_play_with_personality(hand, upcard_value, rules, personality)
                assert action in valid, (
                    f"[{personality}] recomendó {action!r} para {hand} "
                    f"(is_first={is_first}) pero las acciones válidas son {valid}"
                )
