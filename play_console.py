"""
play_console.py — Blackjack Pro en modo consola interactivo
Ejecutar: python play_console.py
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from engine.game_engine import GameEngine
from engine.game_state import GameState, ActionResult, RoundResult
from engine.payout import HandPayout
from ai.basic_strategy import get_basic_strategy, ACTION_COLOR
from ai.card_counter import HiLoCounter
from config.rules_presets import PRESETS, get_preset
from config import settings as cfg

# ──────────────────────────────────────────────────────────────────────
# Colores ANSI para Windows / Unix
# ──────────────────────────────────────────────────────────────────────
try:
    import colorama
    colorama.init(autoreset=True)
    _ANSI = True
except ImportError:
    _ANSI = False

def _c(text: str, code: str) -> str:
    if not _ANSI:
        return text
    return f"\033[{code}m{text}\033[0m"

RED    = lambda t: _c(t, "91")
GREEN  = lambda t: _c(t, "92")
YELLOW = lambda t: _c(t, "93")
BLUE   = lambda t: _c(t, "94")
CYAN   = lambda t: _c(t, "96")
WHITE  = lambda t: _c(t, "97")
BOLD   = lambda t: _c(t, "1")
DIM    = lambda t: _c(t, "2")
GOLD   = lambda t: _c(t, "33")

# Colores de palo
def suit_color(suit: str) -> str:
    if suit in ("♥", "♦"):
        return RED(suit)
    return WHITE(suit)

def card_str(card) -> str:
    if not card.face_up:
        return BLUE("🂠")
    rank = card.rank
    suit = suit_color(card.suit)
    return f"{rank}{suit}"

def hand_display(hand, label: str = "", active: bool = False) -> str:
    cards = " ".join(card_str(c) for c in hand.cards)
    val = hand.value
    soft = " soft" if hand.is_soft else ""
    bj   = GOLD(" ★ BLACKJACK!") if hand.is_blackjack else ""
    bust = RED(" ✗ BUST") if hand.is_bust else ""
    dbl  = YELLOW(" [DOBLÓ]") if hand.is_doubled else ""
    spl  = DIM(" [SPLIT]") if hand.is_split else ""
    bet  = DIM(f"  apuesta: {hand.bet:.0f}")
    arrow = CYAN(" ◄") if active else ""
    prefix = BOLD(label) if label else ""
    return f"{prefix}  {cards}  = {BOLD(str(val))}{soft}{bj}{bust}{dbl}{spl}{bet}{arrow}"

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def separator(char="─", width=58):
    print(DIM(char * width))

def header():
    print(GOLD("""
  ╔══════════════════════════════════════════════╗
  ║       🃏  B L A C K J A C K   P R O  🃏      ║
  ╚══════════════════════════════════════════════╝"""))

# ──────────────────────────────────────────────────────────────────────
# Estado global compartido entre callbacks
# ──────────────────────────────────────────────────────────────────────
_last_payouts: list[HandPayout] = []
_messages: list[str] = []
_counter = HiLoCounter()

def _on_message(msg: str):
    _messages.append(msg)

def _on_round_end(payouts: list[HandPayout]):
    global _last_payouts
    _last_payouts = payouts

# ──────────────────────────────────────────────────────────────────────
# Render del estado de mesa
# ──────────────────────────────────────────────────────────────────────
def render_table(engine: GameEngine, show_hint: bool = True):
    clear()
    header()
    separator()

    rules = engine.rules
    deck  = engine.deck
    player = engine.player
    dealer = engine.dealer

    # Info de reglas y zapato
    print(f"  {DIM(str(rules))}   {DIM(f'Zapato: {deck.cards_remaining}/{deck.total_cards}')}")

    # Contador Hi-Lo
    if cfg.SHOW_CARD_COUNTER:
        _counter.update_deck_estimate(deck)
        tc_color = GREEN if _counter.true_count_rounded >= 2 else (RED if _counter.true_count_rounded <= -2 else YELLOW)
        print(f"  {DIM('Hi-Lo:')} RC={_counter.running_count:+d}  TC={tc_color(f'{_counter.true_count:+.1f}')}  {_counter.count_label}")

    separator()

    # Mano del crupier
    d_cards = " ".join(card_str(c) for c in dealer.hand.cards)
    d_val   = dealer.upcard_value if engine.state in (GameState.PLAYER_TURN, GameState.INSURANCE, GameState.DEALING) else dealer.value
    if engine.state in (GameState.DEALER_TURN, GameState.PAYOUT, GameState.BETTING):
        d_val_str = BOLD(str(dealer.value))
        bj_str = GOLD(" ★ BLACKJACK!") if dealer.has_blackjack else ""
        bust_str = RED(" ✗ BUST") if dealer.is_bust else ""
    else:
        d_val_str = BOLD(str(dealer.upcard_value)) + DIM(" + ?")
        bj_str = bust_str = ""
    print(f"\n  {CYAN('CRUPIER')}  {d_cards}  = {d_val_str}{bj_str}{bust_str}")

    separator("·")

    # Manos del jugador
    print()
    for i, hand in enumerate(player.hands):
        active = (i == player.active_hand_index and engine.state == GameState.PLAYER_TURN)
        label = f"MANO {i+1}" if len(player.hands) > 1 else "TU MANO"
        print(f"  {hand_display(hand, label, active)}")

    print()
    print(f"  {BOLD('Fichas:')} {YELLOW(str(int(player.chips)))}   {DIM(str(player.stats))}")
    separator()

    # Hint de estrategia básica
    if show_hint and engine.state == GameState.PLAYER_TURN:
        hand = player.active_hand
        if hand and not hand.is_finished:
            try:
                hint = get_basic_strategy(hand, dealer.upcard_value, rules)
                hint_label = hint.value
                print(f"  {DIM('Estrategia básica:')} {YELLOW(hint_label)}")
            except Exception:
                pass
        separator()

    # Mensajes pendientes
    for msg in _messages:
        print(f"  {CYAN('►')} {msg}")
    _messages.clear()

# ──────────────────────────────────────────────────────────────────────
# Input helpers
# ──────────────────────────────────────────────────────────────────────
def ask(prompt: str) -> str:
    try:
        return input(prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n\n  Saliendo... ¡hasta pronto!")
        sys.exit(0)

def ask_bet(engine: GameEngine) -> float:
    rules  = engine.rules
    player = engine.player
    suggested = _counter.suggested_bet_units(rules.min_bet) if cfg.SHOW_CARD_COUNTER else rules.min_bet

    while True:
        render_table(engine, show_hint=False)
        print(f"  Mín: {rules.min_bet:.0f}  Máx: {rules.max_bet:.0f}  Fichas: {player.chips:.0f}")
        if cfg.SHOW_CARD_COUNTER:
            print(f"  {DIM('Apuesta sugerida por contador:')} {YELLOW(str(int(suggested)))}")
        raw = ask(f"\n  ¿Cuánto apuestas? [{int(rules.min_bet)}-{int(min(rules.max_bet, player.chips))}]: ")

        if raw in ("q", "quit", "exit", "salir"):
            print("\n  Saliendo... ¡hasta pronto!")
            sys.exit(0)
        if raw in ("s", "stats"):
            from engine.statistics import StatisticsManager
            print(StatisticsManager(player).summary())
            ask("  [Enter para continuar]")
            continue
        if raw in ("c", "contador"):
            cfg.SHOW_CARD_COUNTER = not cfg.SHOW_CARD_COUNTER
            continue
        if raw in ("h", "hint", "hints"):
            cfg.SHOW_HINTS = not cfg.SHOW_HINTS
            continue

        try:
            amount = float(raw)
            if amount <= 0:
                raise ValueError
            return amount
        except ValueError:
            _messages.append(RED(f"Introduce un número válido (mín {rules.min_bet:.0f})."))

def ask_action(engine: GameEngine) -> str:
    actions = engine.get_available_actions()
    shortcuts = {
        "h": "hit",   "1": "hit",
        "s": "stand", "2": "stand",
        "d": "double","3": "double",
        "p": "split", "4": "split",
        "r": "surrender", "5": "surrender",
        "q": "quit",
    }
    # Construir prompt con las acciones disponibles
    opts = []
    num  = 1
    key_map: dict[str, str] = {}
    action_keys = {"hit": "H", "stand": "S", "double": "D", "split": "P", "surrender": "R"}
    for a in actions:
        letter = action_keys.get(a, a[0].upper())
        opts.append(f"{BOLD(letter)}={a.capitalize()}")
        key_map[letter.lower()] = a
        key_map[str(num)] = a
        num += 1

    prompt_str = "  " + "  ".join(opts) + f"  {DIM('(Q=salir)')}: "

    while True:
        render_table(engine, show_hint=cfg.SHOW_HINTS)
        raw = ask(f"\n{prompt_str}")

        if raw in ("q", "quit", "exit"):
            print("\n  Saliendo... ¡hasta pronto!")
            sys.exit(0)

        # Buscar por tecla o nombre completo
        action = key_map.get(raw) or (raw if raw in actions else None)
        if action:
            return action

        _messages.append(RED(f"'{raw}' no es válido. Opciones: {', '.join(actions)}"))

def ask_insurance(engine: GameEngine) -> bool:
    render_table(engine, show_hint=False)
    hand = engine.player.active_hand
    is_bj = hand and hand.is_blackjack

    if is_bj and engine.rules.even_money_allowed:
        print(f"\n  {GOLD('★ Tienes BLACKJACK y el crupier muestra As.')}")
        print(f"  {YELLOW('Even Money')} = cobrar 1:1 ahora y asegurar la ganancia.")
        raw = ask("  ¿Aceptas Even Money? (s/n): ")
    else:
        ins_amount = (hand.bet / 2) if hand else 0
        print(f"\n  {YELLOW('El crupier muestra As.')} ¿Quieres contratar seguro?")
        print(f"  Coste del seguro: {ins_amount:.0f} fichas  (paga 2:1 si el crupier tiene BJ)")
        raw = ask("  ¿Contratas seguro? (s/n): ")

    return raw in ("s", "si", "sí", "y", "yes", "1")

def show_round_result(engine: GameEngine):
    render_table(engine, show_hint=False)
    separator("═")
    print(f"\n  {BOLD('RESULTADO DE LA RONDA:')}\n")

    result_emoji = {
        "WIN": GREEN("✅ GANASTE"),
        "BLACKJACK_WIN": GOLD("🌟 BLACKJACK!"),
        "LOSS": RED("❌ PERDISTE"),
        "PUSH": YELLOW("🤝 EMPATE"),
        "SURRENDER": YELLOW("🏳  RENDICIÓN"),
        "DEALER_BUST": GREEN("💥 CRUPIER SE PASÓ"),
    }

    total_net = 0.0
    for i, p in enumerate(_last_payouts):
        label = f"Mano {i+1}" if len(_last_payouts) > 1 else "Resultado"
        emoji = result_emoji.get(p.result.name, p.result.name)
        net_str = GREEN(f"+{p.net:.0f}") if p.net > 0 else (RED(f"{p.net:.0f}") if p.net < 0 else YELLOW("0"))
        print(f"  {label}: {emoji}   neto: {net_str}")
        total_net += p.net

    if len(_last_payouts) > 1:
        total_str = GREEN(f"+{total_net:.0f}") if total_net > 0 else (RED(f"{total_net:.0f}") if total_net < 0 else YELLOW("0"))
        print(f"\n  {BOLD('Total:')} {total_str}")

    print(f"\n  {BOLD('Fichas:')} {YELLOW(str(int(engine.player.chips)))}")
    separator("═")

# ──────────────────────────────────────────────────────────────────────
# Menú de selección de casino
# ──────────────────────────────────────────────────────────────────────
def select_preset() -> str:
    clear()
    header()
    print(f"\n  {BOLD('Selecciona el preset de casino:')}\n")
    names = list(PRESETS.keys())
    for i, name in enumerate(names, 1):
        rules = get_preset(name)
        print(f"  {BOLD(str(i))}. {CYAN(name)}")
        print(f"     {DIM(str(rules))}\n")
    print(f"  {BOLD(str(len(names)+1))}. {DIM('Personalizado (reglas por defecto)')}\n")

    while True:
        raw = ask("  Elige [1-{}]: ".format(len(names)+1))
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(names):
                return names[idx]
            if idx == len(names):
                return "Vegas Strip"  # fallback a default
        except ValueError:
            pass
        print(RED("  Opción inválida."))

def ask_player_name() -> str:
    clear()
    header()
    name = ask("\n  ¿Cuál es tu nombre? (Enter para 'Jugador'): ")
    return name if name else "Jugador"

def show_help():
    clear()
    header()
    print(f"""
  {BOLD('CONTROLES:')}
  {CYAN('H')} o {CYAN('1')} → Hit        (pedir carta)
  {CYAN('S')} o {CYAN('2')} → Stand       (plantarse)
  {CYAN('D')} o {CYAN('3')} → Double Down (doblar — solo con 2 cartas)
  {CYAN('P')} o {CYAN('4')} → Split       (dividir par)
  {CYAN('R')} o {CYAN('5')} → Surrender   (rendirse — solo primera acción)
  {CYAN('Q')}       → Quit        (salir)

  {BOLD('DURANTE LA APUESTA:')}
  {CYAN('stats')}   → ver estadísticas de sesión
  {CYAN('contador')}→ activar/desactivar contador Hi-Lo
  {CYAN('hints')}   → activar/desactivar estrategia básica

  {BOLD('REGLAS ACTIVAS:')}  mostradas en la parte superior de la mesa
""")
    ask("  [Enter para continuar]")

# ──────────────────────────────────────────────────────────────────────
# Bucle principal
# ──────────────────────────────────────────────────────────────────────
def main():
    clear()
    header()
    print(f"\n  {CYAN('Bienvenido a Blackjack Pro — versión consola')}")
    print(f"  {DIM('Escribe help en cualquier momento para ver los controles.')}\n")

    name   = ask_player_name()
    preset = select_preset()
    rules  = get_preset(preset)

    engine = GameEngine(rules=rules, player_name=name)
    engine.on("on_message",   _on_message)
    engine.on("on_round_end", _on_round_end)

    # Registrar todas las cartas visibles en el contador Hi-Lo
    def _on_card(card, target, idx):
        _counter.register_card(card)
    engine.on("on_card_dealt", _on_card)

    # Resetear contador al rebarajar
    def _on_state(state):
        if state == GameState.BETTING and engine.deck.reshuffle_flag is False:
            pass  # el reset lo haríamos al detectar shuffle; simplificamos
    engine.on("on_state_change", _on_state)

    engine.start_game()
    _counter._decks_estimate = float(rules.num_decks)

    print(f"\n  {GREEN('✓')} Preset: {CYAN(preset)}")
    print(f"  {GREEN('✓')} Fichas iniciales: {YELLOW(str(int(engine.player.chips)))}")
    ask(f"\n  [Enter para empezar]")

    # ── BUCLE DE RONDAS ──────────────────────────────────────────────
    while engine.state not in (GameState.GAME_OVER,):

        # 1. APUESTA
        if engine.state == GameState.BETTING:
            amount = ask_bet(engine)
            if amount == -1:
                break
            ok = engine.place_bet(amount)
            if not ok:
                continue

        # 2. SEGURO / EVEN MONEY
        if engine.state == GameState.INSURANCE:
            accept = ask_insurance(engine)
            engine.accept_insurance(accept)
            # Si la ronda terminó (even money o BJ del crupier) mostrar resultado
            if engine.state == GameState.BETTING:
                show_round_result(engine)
                ask("  [Enter para continuar]")
                continue

        # 3. TURNO DEL JUGADOR
        while engine.state == GameState.PLAYER_TURN:
            action = ask_action(engine)
            result = engine.player_action(action)

            if result == ActionResult.BUST:
                _messages.append(RED("¡Te has pasado!"))
            elif result == ActionResult.BLACKJACK:
                _messages.append(GOLD("¡BLACKJACK!"))
            elif result == ActionResult.TWENTY_ONE:
                _messages.append(GREEN("¡21!"))
            elif result == ActionResult.SPLIT_DONE:
                _messages.append(CYAN("Split realizado. Jugando mano 1..."))

        # 4. TURNO DEL CRUPIER (automático, el engine lo gestiona)
        # Ya terminó cuando salimos del while

        # 5. RESULTADO
        if engine.state in (GameState.BETTING, GameState.GAME_OVER):
            show_round_result(engine)
            if engine.state == GameState.GAME_OVER:
                break
            ask("  [Enter para siguiente ronda]")

    # ── GAME OVER ────────────────────────────────────────────────────
    clear()
    header()
    print(f"\n  {RED(BOLD('¡GAME OVER!'))}")
    print(f"  {name}, te has quedado sin fichas.\n")
    from engine.statistics import StatisticsManager
    print(StatisticsManager(engine.player).summary())
    print(f"\n  {DIM('¡Gracias por jugar!')}\n")


if __name__ == "__main__":
    main()