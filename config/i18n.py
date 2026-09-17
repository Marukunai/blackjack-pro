# config/i18n.py
# Fase 26: sistema de traducción (español/inglés) para toda la UI.
#
# Patrón deliberadamente simple, igual que los temas visuales de
# config/settings.py (apply_table_theme/apply_card_back_theme): LANGUAGE
# vive como atributo mutable de config.settings y se lee EN CADA llamada
# a t() (nunca se cachea), así que cambiarlo en caliente desde
# ui/settings_screen.py basta para que absolutamente toda la UI ya
# dibujada en el siguiente frame salga en el idioma nuevo -- no hace
# falta reconstruir ninguna pantalla.
#
# Las claves usan notación "modulo.algo" solo para organizarlas mejor en
# este archivo; no tienen ningún significado especial para t().
# -------------------------------------------------------------
from __future__ import annotations

from config import settings as cfg


STRINGS: dict[str, dict[str, str]] = {
    "es": {},
    "en": {},
}


def _add(key: str, es: str, en: str) -> None:
    STRINGS["es"][key] = es
    STRINGS["en"][key] = en


def t(key: str, **kwargs) -> str:
    """Devuelve el texto traducido para `key` en el idioma actual
    (`cfg.LANGUAGE`, leído en vivo). Si faltase la clave en el idioma
    activo cae al español; si faltase en los dos, devuelve la propia
    clave (para que un texto sin traducir sea visible/detectable en vez
    de reventar)."""
    lang = getattr(cfg, "LANGUAGE", "es")
    table = STRINGS.get(lang) or STRINGS["es"]
    s = table.get(key, STRINGS["es"].get(key, key))
    if kwargs:
        try:
            return s.format(**kwargs)
        except Exception:
            return s
    return s


# ------------------------------------------------------------------
# Botones / acciones de la mesa (Fase 18-26: los nombres de acción de
# blackjack -- Hit/Stand/Double/Split/Surrender -- se dejan siempre en
# inglés incluso en español, como en cualquier mesa real; solo se
# traduce el texto de seguro/even-money).
# ------------------------------------------------------------------
_add("insurance.yes", "Seguro (Sí)", "Insurance (Yes)")
_add("insurance.no", "No", "No")

# ------------------------------------------------------------------
# Mesa (ui/table.py)
# ------------------------------------------------------------------
_add("table.dealer_label", "CRUPIER  {value}", "DEALER  {value}")
_add("table.hand_label", "TU MANO  {value}", "YOUR HAND  {value}")
_add("table.bet_label", "Apuesta: {bet}", "Bet: {bet}")

# ------------------------------------------------------------------
# ui/chip_stack.py
# ------------------------------------------------------------------
_add("chipstack.undo_hint", "Click derecho -> devolver última ficha",
     "Right-click -> return last chip")

# ------------------------------------------------------------------
# Catálogos de datos (logros / desafíos / presets / temas): en vez de
# claves genéricas t("achievement.xxx.name") -- que si faltase alguna
# se verían literalmente en pantalla -- se usan diccionarios propios +
# funciones ayudante con fallback seguro al texto español original
# (ach.name/ch.name/nombre de preset), igual que ya hace `t()` pero sin
# depender de que la clave exista: si falta la traducción EN, se ve el
# texto en español en vez de una clave sin traducir.
# ------------------------------------------------------------------

# engine/achievements.py -- id -> (nombre_en, descripción_en)
_ACHIEVEMENTS_EN: dict[str, tuple[str, str]] = {
    "first_win":      ("First win", "Win your first hand."),
    "streak_5":       ("On a roll", "Win 5 hands in a row."),
    "streak_10":      ("Unstoppable", "Win 10 hands in a row."),
    "first_bj":       ("Blackjack!", "Get your first natural Blackjack."),
    "bj_10":          ("House ace", "Get 10 Blackjacks."),
    "hands_100":      ("A hundred hands", "Play 100 hands."),
    "hands_1000":     ("A thousand hands", "Play 1000 hands."),
    "high_roller":    ("High roller", "Reach 5000 chips."),
    "whale":          ("Whale", "Reach 10000 chips."),
    "comeback":       ("Comeback", "Recover after nearly going broke."),
    "first_split":    ("Divide and conquer", "Make your first split."),
    "split_master":   ("Split specialist", "Make 10 splits."),
    "iron_stomach":   ("Iron stomach", "Bust 25 times."),
    "hands_500":      ("Regular", "Play 500 hands."),
    "streak_15":      ("Legendary streak", "Win 15 hands in a row."),
    "bj_25":          ("Blackjack king", "Get 25 Blackjacks."),
    "busts_50":       ("Bulletproof", "Bust 50 times."),
    "first_surrender": ("Tactical retreat", "Surrender for the first time."),
    "first_push":     ("Push", "Tie with the dealer for the first time."),
    "magnate":        ("Magnate", "Reach 25000 chips."),
    "profitable":     ("Clean books", "Finish in profit after at least 50 hands."),
}

# engine/challenges.py -- id -> (nombre_en, descripción_en)
_CHALLENGES_EN: dict[str, tuple[str, str]] = {
    "meta_rapida": ("Quick Target", "Reach $1500 in chips before 20 hands run out."),
    "superviviente": ("Survivor", "Play 25 hands in a row without running out of chips. "
                                   "You start short on cash -- watch your bets."),
    "racha_hierro": ("Iron Streak", "Win 5 hands in a row without losing a single one "
                                     "along the way. One slip and it's over."),
    "contrarreloj": ("Against the Clock", "Finish exactly 15 hands with more chips than "
                                           "you started with."),
}


def achievement_text(ach) -> tuple[str, str]:
    """(nombre, descripción) del logro en el idioma activo; si falta la
    traducción EN, cae al español (nunca se queda en blanco)."""
    if getattr(cfg, "LANGUAGE", "es") == "en":
        pair = _ACHIEVEMENTS_EN.get(ach.id)
        if pair:
            return pair
    return ach.name, ach.description


def challenge_text(ch) -> tuple[str, str]:
    """(nombre, descripción) del desafío en el idioma activo."""
    if getattr(cfg, "LANGUAGE", "es") == "en":
        pair = _CHALLENGES_EN.get(ch.id)
        if pair:
            return pair
    return ch.name, ch.description


# config/rules_presets.py -- nombre interno (clave de PRESETS, no se
# toca) -> nombre a mostrar en inglés. Los que no aparecen aquí (Vegas
# Strip, Atlantic City, European, Single Deck, Downtown Vegas, Macau,
# High Roller) son ya nombres propios en inglés y se muestran igual en
# los dos idiomas.
_PRESET_NAMES_EN: dict[str, str] = {
    "Reglas de Casa": "House Rules",
    "Personalizado": "Custom",
}


def preset_label(name: str) -> str:
    if getattr(cfg, "LANGUAGE", "es") == "en":
        return _PRESET_NAMES_EN.get(name, name)
    return name


# engine/side_bets.py -- SideBetOutcome.label es un identificador propio
# en español (también aparece como CLAVE en PERFECT_PAIRS_PAYOUTS /
# TWENTYONE_PLUS_THREE_PAYOUTS, así que nunca se toca) -> traducción
# solo para mostrar en pantalla.
_SIDE_BET_LABELS_EN: dict[str, str] = {
    "Sin pareja": "No pair",
    "Pareja perfecta": "Perfect pair",
    "Pareja de color": "Colored pair",
    "Pareja mixta": "Mixed pair",
    "Sin premio": "No win",
    "Trío de color": "Suited trips",
    "Escalera de color": "Straight flush",
    "Trío": "Three of a kind",
    "Escalera": "Straight",
    "Color": "Flush",
}


def side_bet_label(label: str) -> str:
    if getattr(cfg, "LANGUAGE", "es") == "en":
        return _SIDE_BET_LABELS_EN.get(label, label)
    return label


# config/settings.py -- TABLE_THEMES / CARD_BACK_THEMES: clave interna
# (no se toca, se usa para persistir en app_settings.json) -> etiqueta
# a mostrar en inglés.
_TABLE_THEME_LABELS_EN: dict[str, str] = {
    "classic_green": "Classic green",
    "royal_blue":    "Royal blue",
    "burgundy":      "Burgundy",
    "midnight":      "Midnight black",
}
_CARD_BACK_LABELS_EN: dict[str, str] = {
    "green_gold":  "Green & gold",
    "red_classic": "Classic red",
    "blue_royal":  "Royal blue",
}


def table_theme_label(key: str, fallback_es: str) -> str:
    if getattr(cfg, "LANGUAGE", "es") == "en":
        return _TABLE_THEME_LABELS_EN.get(key, fallback_es)
    return fallback_es


def card_back_label(key: str, fallback_es: str) -> str:
    if getattr(cfg, "LANGUAGE", "es") == "en":
        return _CARD_BACK_LABELS_EN.get(key, fallback_es)
    return fallback_es


# ------------------------------------------------------------------
# engine/challenges.py -- Challenge.progress_label() (plantillas
# dinámicas de la barra de progreso del banner de Desafío)
# ------------------------------------------------------------------
_add("challenge.progress_chips", "${chips} / ${target}", "${chips} / ${target}")
_add("challenge.progress_streak", "Racha {cur} / {target}", "Streak {cur} / {target}")
_add("challenge.progress_net", "Neto: {net:+.0f}", "Net: {net:+.0f}")
_add("challenge.progress_hand", "Mano {hand} / {limit}", "Hand {hand} / {limit}")

# ------------------------------------------------------------------
# Claves generadas por el resto de pantallas (perfiles, historial,
# comparativa, selección de desafío, apuestas laterales, repetición).
# ------------------------------------------------------------------
_add('profile.title_default', '¿Quién juega?', "Who's playing?")
_add('profile.subtitle_default', 'Perfiles locales — sin contraseña, cada uno con su propio historial', 'Local profiles — no password, each with its own history')
_add('profile.subtitle_seat', 'Elige quién se sienta en el siguiente asiento', 'Choose who sits in the next seat')
_add('profile.leaderboard_button', 'Comparativa', 'Leaderboard')
_add('profile.new_profile_button', '+  Nuevo perfil', '+  New profile')
_add('profile.list_hint', 'Click en un perfil para continuar · lista: ver historial · papelera: borrar · N: nuevo perfil · Comparativa: comparar perfiles', 'Click a profile to continue · list icon: view history · trash icon: delete · N: new profile · Leaderboard: compare profiles')
_add('profile.confirm_delete', '¿Borrar? Click de nuevo para confirmar', 'Delete? Click again to confirm')
_add('profile.chips_hands_info', '{chips:.0f} fichas · {hands} manos jugadas', '{chips:.0f} chips · {hands} hands played')
_add('profile.create_title', 'Nuevo perfil', 'New profile')
_add('profile.name_label', 'Nombre:', 'Name:')
_add('profile.avatar_label', 'Avatar:', 'Avatar:')
_add('profile.create_button', 'Crear', 'Create')
_add('profile.cancel_button', 'Cancelar', 'Cancel')
_add('profile.error_empty_name', 'Escribe un nombre para el perfil.', 'Enter a name for the profile.')
_add('profile.create_hint', 'Flechas para elegir avatar · Enter para crear · Esc para volver', 'Arrows to choose avatar · Enter to create · Esc to go back')
_add('profile.seats_title', 'Jugadores en la mesa', 'Players at the table')
_add('profile.seat_number', 'Asiento {n}', 'Seat {n}')
_add('profile.add_player_button', '+  Añadir jugador', '+  Add player')
_add('profile.max_players_note', 'Máximo 3 jugadores en la mesa', 'Maximum 3 players at the table')
_add('profile.play_button', 'Jugar', 'Play')
_add('profile.play_solo_button', 'Jugar en solitario', 'Play solo')
_add('profile.seats_hint_play', 'Enter para jugar', 'Enter to play')
_add('profile.seats_hint_add', ' · A para añadir otro jugador', ' · A to add another player')
_add('history.col_date', 'Fecha', 'Date')
_add('history.col_casino', 'Casino', 'Casino')
_add('history.col_bet', 'Apuesta', 'Bet')
_add('history.col_result', 'Resultado', 'Result')
_add('history.col_net', 'Neto', 'Net')
_add('history.col_chips', 'Fichas', 'Chips')
_add('history.result_win', 'Ganaste', 'You won')
_add('history.result_blackjack_win', '¡Blackjack!', 'Blackjack!')
_add('history.result_dealer_bust', 'Crupier se pasó', 'Dealer busted')
_add('history.result_loss', 'Perdiste', 'You lost')
_add('history.result_push', 'Empate', 'Push')
_add('history.result_surrender', 'Rendición', 'Surrender')
_add('history.default_player_name', 'Jugador', 'Player')
_add('history.title_for_profile', 'Historial de {name}', 'History for {name}')
_add('history.empty_state', 'Todavía no hay manos jugadas con este perfil.', 'No hands played yet with this profile.')
_add('history.chip_evolution_label', 'Evolución de fichas (últimas {n} manos)', 'Chip evolution (last {n} hands)')
_add('history.pagination_label', 'Página {page} / {total_pages}  ·  {total} manos en total', 'Page {page} / {total_pages}  ·  {total} hands total')
_add('history.back_button', 'Volver', 'Back')
_add('history.hint_page_arrows', 'Flechas para cambiar de página', 'Arrows to change page')
_add('history.hint_esc_exit', 'Esc/Volver para salir', 'Esc/Back to exit')
_add('history.hint_tab_switch', 'Tab para cambiar de perfil', 'Tab to switch profile')
_add('leaderboard.col_rank', '#', '#')
_add('leaderboard.col_name', 'Perfil', 'Profile')
_add('leaderboard.col_chips', 'Fichas', 'Chips')
_add('leaderboard.col_hands', 'Manos', 'Hands')
_add('leaderboard.col_win_pct', '% Victorias', '% Wins')
_add('leaderboard.col_blackjacks', 'Blackjacks', 'Blackjacks')
_add('leaderboard.col_best_streak', 'Mejor racha', 'Best streak')
_add('leaderboard.col_achievements', 'Logros', 'Achievements')
_add('leaderboard.title', 'Comparativa de perfiles', 'Profile leaderboard')
_add('leaderboard.sort_hint', 'Click en una columna para ordenar por ella', 'Click a column to sort by it')
_add('leaderboard.empty_state', 'Todavía no hay perfiles para comparar.', 'There are no profiles to compare yet.')
_add('leaderboard.back_button', 'Volver', 'Back')
_add('leaderboard.hint_esc_exit', 'Esc/Volver para salir', 'Esc/Back to exit')
_add('challenge_select.title', 'DESAFÍOS', 'CHALLENGES')
_add('challenge_select.subtitle', 'Partidas cortas con un objetivo concreto -- ideal para una sesión rápida', 'Short games with a concrete goal -- ideal for a quick session')
_add('challenge_select.item_facts', '{limit} manos · ${chips} iniciales', '{limit} hands · ${chips} starting')
_add('challenge_select.detail_hand_limit', 'Límite de manos: {limit}', 'Hand limit: {limit}')
_add('challenge_select.detail_starting_chips', 'Fichas iniciales: ${chips}', 'Starting chips: ${chips}')
_add('challenge_select.detail_bet_range', 'Apuesta: ${min} - ${max}', 'Bet: ${min} - ${max}')
_add('challenge_select.detail_target_chips', 'Objetivo: llegar a ${target} en fichas', 'Goal: reach ${target} in chips')
_add('challenge_select.detail_target_streak', 'Objetivo: racha de {streak} victorias seguidas', 'Goal: a streak of {streak} wins in a row')
_add('challenge_select.detail_fail_on_loss', 'Cualquier derrota, pasada o rendición termina el desafío', 'Any loss, push or surrender ends the challenge')
_add('challenge_select.detail_require_profit', 'Objetivo: acabar con más fichas de las que empezaste', 'Goal: finish with more chips than you started with')
_add('challenge_select.back_button', 'Volver', 'Back')
_add('challenge_select.start_button', 'Empezar Desafío', 'Start Challenge')
_add('challenge_select.hint', 'Flechas para moverte · Enter/Empezar confirma · Esc/Volver cancela', 'Arrows to move · Enter/Start confirms · Esc/Back cancels')
_add('sidebets.perfect_pairs_label', 'Parejas Perfectas', 'Perfect Pairs')
_add('sidebets.title', 'Apuestas laterales (opcional)', 'Side bets (optional)')
_add('replay.no_data', 'No hay datos de repetición guardados para esta mano.', 'No replay data saved for this hand.')
_add('replay.parse_error', 'No se pudo interpretar la repetición de esta mano.', 'Could not read the replay for this hand.')
_add('replay.dealer_label_value', 'CRUPIER  {value}', 'DEALER  {value}')
_add('replay.dealer_label_empty', 'CRUPIER', 'DEALER')
_add('replay.player_label_value', 'TU MANO  {value}{tags}', 'YOUR HAND  {value}{tags}')
_add('replay.player_label_empty', 'TU MANO', 'YOUR HAND')
_add('replay.tag_doubled', 'doblada', 'doubled')
_add('replay.tag_surrendered', 'rendida', 'surrendered')
_add('replay.info_bar', '{date}   ·   {preset}   ·   Apuesta: ${bet:.0f}', '{date}   ·   {preset}   ·   Bet: ${bet:.0f}')
_add('replay.back_button', 'Volver', 'Back')
_add('replay.exit_hint', 'Esc/Volver para salir', 'Esc/Back to exit')

# ------------------------------------------------------------------
# ui/menu.py (MainMenu + RulesEditor)
# ------------------------------------------------------------------
_add("menu.player_label", "Jugador: {name}", "Player: {name}")
_add("menu.select_casino", "Selecciona el casino:", "Select a casino:")
_add("menu.custom_option", "Personalizado...", "Custom...")
_add("menu.custom_hint", "Pulsa Enter o JUGAR para ajustar tus propias reglas",
     "Press Enter or PLAY to set up your own rules")
_add("menu.play_button", "JUGAR", "PLAY")
_add("menu.hint_base", "Flechas arriba/abajo para seleccionar · Enter para jugar",
     "Up/down arrows to select · Enter to play")
_add("menu.hint_history_suffix", " · H: historial", " · H: history")
_add("menu.history_button", "Historial", "History")
_add("menu.challenges_button", "Desafíos", "Challenges")
_add("menu.settings_button", "Ajustes", "Settings")
_add("menu.rules_editor_title", "REGLAS PERSONALIZADAS", "CUSTOM RULES")
_add("menu.reset_button", "Restablecer", "Reset")
_add("menu.rules_hint", "Flechas para moverte y cambiar valores · Enter/JUGAR confirma · Esc/Volver cancela",
     "Arrows to move and change values · Enter/PLAY confirms · Esc/Back cancels")
_add("menu.back_button", "Volver", "Back")

_add("menu.field.num_decks", "Mazos", "Decks")
_add("menu.field.penetration", "Penetración del zapato", "Shoe penetration")
_add("menu.field.dealer_rule", "Crupier en soft 17", "Dealer on soft 17")
_add("menu.field.blackjack_payout", "Pago de Blackjack", "Blackjack payout")
_add("menu.field.double_rule", "Doblar permitido con", "Doubling allowed on")
_add("menu.field.double_after_split", "Doblar tras split (DAS)", "Double after split (DAS)")
_add("menu.field.max_splits", "Splits máximos", "Max splits")
_add("menu.field.resplit_aces", "Re-splitear Ases", "Re-split Aces")
_add("menu.field.hit_split_aces", "Pedir tras splitear Ases", "Hit after splitting Aces")
_add("menu.field.surrender_rule", "Rendirse (Surrender)", "Surrender")
_add("menu.field.insurance_allowed", "Seguro permitido", "Insurance allowed")
_add("menu.field.even_money_allowed", "Even Money", "Even Money")
_add("menu.field.min_bet", "Apuesta mínima", "Minimum bet")
_add("menu.field.max_bet", "Apuesta máxima", "Maximum bet")
_add("menu.field.starting_chips", "Fichas iniciales", "Starting chips")
_add("menu.field.five_card_charlie", "Five Card Charlie", "Five Card Charlie")
_add("menu.field.original_bets_only", "OBBO (BJ del crupier)", "OBBO (dealer BJ)")
_add("menu.field.perfect_pairs_allowed", "Apuesta lateral: Parejas Perfectas", "Side bet: Perfect Pairs")
_add("menu.field.twentyone_plus_three_allowed", "Apuesta lateral: 21+3", "Side bet: 21+3")
_add("menu.field.side_bet_max", "Tope de apuesta lateral", "Side bet limit")

_add("menu.yes", "Sí", "Yes")
_add("menu.no", "No", "No")
_add("menu.dealer_stand_s17", "Planta (S17)", "Stands (S17)")
_add("menu.dealer_hit_h17", "Pide (H17)", "Hits (H17)")
_add("menu.double_any_two", "Cualquier 2 cartas", "Any 2 cards")
_add("menu.double_9_10_11", "Solo 9, 10 u 11", "Only 9, 10 or 11")
_add("menu.surrender_none", "No permitido", "Not allowed")
_add("menu.surrender_late", "Tardío", "Late")
_add("menu.surrender_early", "Temprano", "Early")
_add("menu.max_splits_fmt", "{v} (hasta {n} manos)", "{v} (up to {n} hands)")

# ------------------------------------------------------------------
# ui/renderer.py
# ------------------------------------------------------------------
_add("renderer.title_add_seat", "¿Quién se sienta también?", "Who else is sitting down?")
_add("renderer.challenge_preset_label", "Desafío: {name}", "Challenge: {name}")
_add("renderer.training_mode_toggle", "Modo entrenamiento {state}", "Training mode {state}")
_add("renderer.training_on", "activado", "on")
_add("renderer.training_off", "desactivado", "off")
_add("renderer.min_bet_warning", "Apuesta mínima: ${amount}", "Minimum bet: ${amount}")
_add("renderer.natural_blackjack", "¡Blackjack de {name}!", "{name} has Blackjack!")
_add("renderer.dealer_reveals", "El crupier destapa su carta...", "The dealer reveals their card...")
_add("renderer.result_blackjack", "BLACKJACK!", "BLACKJACK!")
_add("renderer.result_win", "GANASTE", "YOU WON")
_add("renderer.result_loss", "PERDISTE", "YOU LOST")
_add("renderer.result_surrender", "RENDICIÓN", "SURRENDER")
_add("renderer.result_push", "EMPATE", "PUSH")
_add("renderer.result_dealer_bust", "CRUPIER SE PASÓ", "DEALER BUSTED")
_add("renderer.sidebet_perfect_pairs", "Parejas Perfectas", "Perfect Pairs")
_add("renderer.reshuffling", "Rebarajando", "Reshuffling")
_add("renderer.action_hit", "Pedir carta", "Hit")
_add("renderer.action_stand", "Plantarse", "Stand")
_add("renderer.action_double", "Doblar", "Double")
_add("renderer.action_split", "Dividir", "Split")
_add("renderer.action_surrender", "Rendirse", "Surrender")
_add("renderer.training_correct", "¡Correcto!", "Correct!")
_add("renderer.training_should_have", "Estrategia básica: {label}", "Basic strategy: {label}")
_add("renderer.dealer_busts", "¡El crupier se pasa!", "The dealer busts!")
_add("renderer.dealer_blackjack", "El crupier tiene Blackjack", "The dealer has Blackjack")
_add("renderer.dealer_stands", "El crupier se planta en {value}", "The dealer stands on {value}")
_add("renderer.dealer_hits", "El crupier pide carta...", "The dealer hits...")
_add("renderer.even_money_or_insurance", "¿Even Money o Seguro?", "Even Money or Insurance?")
_add("renderer.dealer_shows_ace", "El crupier muestra As — ¿Seguro?", "The dealer shows an Ace — Insurance?")
_add("renderer.shoe_info", "Zapato: {remaining}/{total}", "Shoe: {remaining}/{total}")
_add("renderer.betting_turn", "Turno de apuesta: {name}", "Betting turn: {name}")
_add("renderer.deal_button", "DEAL", "DEAL")
_add("renderer.rebet_button", "Repetir ${amount}", "Rebet ${amount}")
_add("renderer.betting_hint", "Haz clic en las fichas para apostar · Enter para repartir",
     "Click the chips to bet · Enter to deal")
_add("renderer.dealing_to", "Repartiendo a {name}...", "Dealing to {name}...")
_add("renderer.hand_n_label", "Mano {n}: ", "Hand {n}: ")
_add("renderer.total_label", "Total: {sign}{amount}", "Total: {sign}{amount}")
_add("renderer.continue_hint", "Click o Enter para continuar", "Click or Enter to continue")
_add("renderer.n_hands", "{n} manos", "{n} hands")
_add("renderer.player_n_fallback", "Jugador {n}", "Player {n}")
_add("renderer.round_result_title", "RESULTADO DE LA RONDA", "ROUND RESULT")
_add("renderer.game_over_title", "GAME OVER", "GAME OVER")
_add("renderer.hands_played_stat", "Manos jugadas: {n}", "Hands played: {n}")
_add("renderer.wlp_stat", "W / L / P:  {w} / {l} / {p}", "W / L / P:  {w} / {l} / {p}")
_add("renderer.net_roi_stat", "Neto: {net:+.0f}   ROI: {roi:+.1%}", "Net: {net:+.0f}   ROI: {roi:+.1%}")
_add("renderer.esc_to_menu", "ESC -> Menú principal", "ESC -> Main menu")
_add("renderer.challenge_won_title", "¡DESAFÍO SUPERADO!", "CHALLENGE COMPLETE!")
_add("renderer.challenge_lost_title", "DESAFÍO FALLIDO", "CHALLENGE FAILED")
_add("renderer.final_chips_net_stat", "Fichas finales: {chips}   Neto: {net:+.0f}",
     "Final chips: {chips}   Net: {net:+.0f}")
_add("renderer.seat_doubles", "DOBLA", "DOUBLES")
_add("renderer.seat_split_aces", "ASES", "ACES")
_add("renderer.seat_blackjack", "¡BLACKJACK!", "BLACKJACK!")
_add("renderer.split_aces_result", "{name} separa los Ases: {v1} y {v2}",
     "{name} splits Aces: {v1} and {v2}")
_add("renderer.blackjack_bang", "¡Blackjack!", "Blackjack!")

# ------------------------------------------------------------------
# engine/game_engine.py -- mensajes emitidos vía el evento "on_message"
# (los recibe ui/renderer.py::_on_engine_message y los muestra como un
# toast flotante; el motor no sabe nada de pygame ni de i18n más allá
# de esta llamada a t()).
# ------------------------------------------------------------------
_add("engine.invalid_bet", "Apuesta inválida. Min={min}, Max={max}", "Invalid bet. Min={min}, Max={max}")
_add("engine.invalid_side_bet", "Apuesta lateral inválida. Max={max}", "Invalid side bet. Max={max}")
_add("engine.not_enough_chips", "No tienes suficientes fichas.", "You don't have enough chips.")
_add("engine.action_unavailable", "Acción '{action}' no disponible ahora.", "Action '{action}' not available right now.")
_add("engine.even_money_paid", "{name}: Even Money cobrado.", "{name}: Even Money paid.")
_add("engine.out_of_chips", "¡Te has quedado sin fichas! Partida terminada.", "You've run out of chips! Game over.")
_add("engine.dealer_has_blackjack", "¡El crupier tiene Blackjack!", "The dealer has Blackjack!")
_add("engine.reshuffling", "Rebarajando el zapato...", "Reshuffling the shoe...")

# ------------------------------------------------------------------
# ui/renderer.py -- tira de asientos (_seat_status_text)
# ------------------------------------------------------------------
_add("renderer.status_betting", "apostando", "betting")
_add("renderer.status_dealing", "repartiendo", "dealing")
_add("renderer.status_insurance", "seguro", "insurance")
_add("renderer.status_playing", "jugando", "playing")
_add("renderer.status_in_game", "en juego", "in game")
_add("renderer.status_waiting", "esperando", "waiting")
_add("renderer.status_bust", "pasada ({value})", "bust ({value})")
_add("renderer.status_stood", "plantado ({value})", "stands ({value})")
_add("renderer.status_hand_value", "mano: {value}", "hand: {value}")
_add("renderer.double_and_bust", "{name} dobla y se pasa ({value})", "{name} doubles and busts ({value})")
_add("renderer.double_result", "{name} dobla: {value}", "{name} doubles: {value}")

# ------------------------------------------------------------------
# ui/hud.py
# ------------------------------------------------------------------
_add("hud.action_double_or_hit", "Double (si no, Hit)", "Double (else Hit)")
_add("hud.action_double_or_stand", "Double (si no, Stand)", "Double (else Stand)")
_add("hud.action_split_or_hit", "Split (si no, Hit)", "Split (else Hit)")
_add("hud.action_surrender_or_hit", "Surrender (si no, Hit)", "Surrender (else Hit)")
_add("hud.action_surrender_or_stand", "Surrender (si no, Stand)", "Surrender (else Stand)")
_add("hud.action_surrender_or_split", "Surrender (si no, Split)", "Surrender (else Split)")
_add("hud.challenge_hands_progress", "Mano {played}/{limit}", "Hand {played}/{limit}")
_add("hud.strategy_hint", "Estrategia: {label}", "Strategy: {label}")
_add("hud.training_badge", "Entrenamiento: {correct}/{total} ({pct:.0f}%)", "Training: {correct}/{total} ({pct:.0f}%)")
_add("hud.category_blackjack", "Blackjack", "Blackjack")
_add("hud.category_win", "Victoria", "Win")
_add("hud.category_push", "Empate", "Push")
_add("hud.category_loss", "Derrota", "Loss")
_add("hud.category_bust", "Pasada", "Bust")
_add("hud.category_surrender", "Rendición", "Surrender")
_add("hud.stat_player", "Jugador: {name}", "Player: {name}")
_add("hud.stat_chips", "Fichas:  {chips}", "Chips:  {chips}")
_add("hud.stat_hands", "Manos:   {n}", "Hands:   {n}")
_add("hud.stat_wlp", "W / L / P: {w} / {l} / {p}", "W / L / P: {w} / {l} / {p}")
_add("hud.stat_winrate", "Winrate: {pct:.1%}", "Win rate: {pct:.1%}")
_add("hud.stat_roi", "ROI:     {roi:+.1%}", "ROI:     {roi:+.1%}")
_add("hud.stat_net", "Neto:    {net:+.0f}", "Net:     {net:+.0f}")
_add("hud.stat_blackjacks", "Blackjacks: {n}", "Blackjacks: {n}")
_add("hud.stat_busts", "Busts:      {n}", "Busts:      {n}")
_add("hud.stat_best_streak", "Mejor racha: +{n}", "Best streak: +{n}")
_add("hud.result_distribution_title", "Distribución de resultados", "Result distribution")
_add("hud.category_count_label", "{label}: {n}", "{label}: {n}")
_add("hud.streak_sparkline_title", "Racha de la sesión (actual: {current:+d})", "Session streak (current: {current:+d})")
_add("hud.achievements_title", "Logros  ({n}/{total})", "Achievements  ({n}/{total})")

# ------------------------------------------------------------------
# ui/animations.py (AchievementToast)
# ------------------------------------------------------------------
_add("animations.achievement_unlocked", "LOGRO DESBLOQUEADO", "ACHIEVEMENT UNLOCKED")
_add("animations.achievement_for_player", "LOGRO DE {name}", "ACHIEVEMENT FOR {name}")

# ------------------------------------------------------------------
# ui/settings_screen.py
# ------------------------------------------------------------------
_add("settings.table_section", "Mesa", "Table")
_add("settings.card_back_section", "Reverso de cartas", "Card back")
_add("settings.audio_section", "Audio", "Audio")
_add("settings.language_section", "Idioma", "Language")
_add("settings.music_label", "Música", "Music")
_add("settings.sfx_label", "Efectos", "Sound effects")
_add("settings.muted", "Silenciado", "Muted")
_add("settings.hint", "Click para aplicar al instante · arrastra los sliders de volumen · Esc/Volver para salir",
     "Click to apply instantly · drag the volume sliders · Esc/Back to exit")

# ------------------------------------------------------------------
# ai/card_counter.py -- etiqueta de "temperatura" del contador Hi-Lo
# ------------------------------------------------------------------
_add("counter.very_cold", "Muy frío 🥶", "Very cold 🥶")
_add("counter.cold", "Frío ❄️", "Cold ❄️")
_add("counter.neutral", "Neutral ➖", "Neutral ➖")
_add("counter.warm", "Tibio 🌡️", "Warm 🌡️")
_add("counter.hot", "Caliente 🔥", "Hot 🔥")
_add("counter.very_hot", "¡Muy caliente! 🌋", "Very hot! 🌋")

_add("renderer.keybinds_hint", "F1: Hints  F2: Contador  F3: Stats  F4: Logros  F5: Entrenamiento  M: Música  ESC: Menú",
     "F1: Hints  F2: Counter  F3: Stats  F4: Achievements  F5: Training  M: Music  ESC: Menu")

# ------------------------------------------------------------------
# engine/profile_store.py
# ------------------------------------------------------------------
_add("profile_store.empty_name", "El nombre no puede estar vacío.", "The name can't be empty.")
_add("profile_store.duplicate_name", "Ya existe un perfil llamado «{name}».", "A profile named «{name}» already exists.")
