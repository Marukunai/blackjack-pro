"""
main.py — Punto de entrada de Blackjack Pro
Ejecutar: python main.py
"""
import sys
from pathlib import Path

# Asegurar que el directorio raíz esté en el path
sys.path.insert(0, str(Path(__file__).resolve().parent))


def main() -> None:
    # Fase 1: verificar que la lógica core funciona (sin UI)
    from engine.game_engine import GameEngine
    from config.rules_presets import get_preset

    print("=" * 50)
    print("  🃏  BLACKJACK PRO — v0.1 (core only)")
    print("=" * 50)

    rules = get_preset("Vegas Strip")
    print(f"\n  Reglas activas: {rules}")

    engine = GameEngine(rules=rules, player_name="Player 1")

    # Registrar callbacks de consola para ver el flujo
    engine.on("on_state_change", lambda s: print(f"  [STATE] → {s.name}"))
    engine.on("on_card_dealt",   lambda c, t, i: print(f"  [CARD]  {t}[{i}] ← {c}"))
    engine.on("on_message",      lambda m: print(f"  [MSG]   {m}"))
    engine.on("on_round_end",    lambda p: print(f"  [ROUND] {engine.get_round_summary()}"))

    engine.start_game()

    print(f"\n  Fichas iniciales: {engine.player.chips:.0f}")
    print(f"  Zapato: {engine.deck}")

    # Simular una ronda de demostración
    print("\n" + "─" * 50)
    print("  RONDA DE DEMOSTRACIÓN")
    print("─" * 50)

    engine.place_bet(25)

    # Si hay oferta de seguro, rechazar
    from engine.game_state import GameState
    if engine.state == GameState.INSURANCE:
        print("  → Rechazando seguro/even money")
        engine.accept_insurance(False)

    # Jugar: mostrar acciones disponibles y plantarse
    from engine.game_state import GameState as GS
    if engine.state == GS.PLAYER_TURN:
        actions = engine.get_available_actions()
        print(f"  Acciones disponibles: {actions}")
        engine.player_action("stand")

    print(f"\n  Fichas finales: {engine.player.chips:.0f}")
    print(f"\n{engine.player.stats}")

    print("\n" + "=" * 50)
    print("  ✅  Core OK — Listo para Fase 2 (UI Pygame)")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()