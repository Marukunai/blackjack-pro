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
    "fr": {},
    "pt": {},
    "de": {},
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

# engine/achievements.py -- id -> (nombre, descripción) por idioma
_ACHIEVEMENTS_EN: dict[str, tuple[str, str]] = {
    'bj_10': ('House ace', 'Get 10 Blackjacks.'),
    'bj_25': ('Blackjack king', 'Get 25 Blackjacks.'),
    'busts_50': ('Bulletproof', 'Bust 50 times.'),
    'comeback': ('Comeback', 'Recover after nearly going broke.'),
    'first_bj': ('Blackjack!', 'Get your first natural Blackjack.'),
    'first_push': ('Push', 'Tie with the dealer for the first time.'),
    'first_split': ('Divide and conquer', 'Make your first split.'),
    'first_surrender': ('Tactical retreat', 'Surrender for the first time.'),
    'first_win': ('First win', 'Win your first hand.'),
    'hands_100': ('A hundred hands', 'Play 100 hands.'),
    'hands_1000': ('A thousand hands', 'Play 1000 hands.'),
    'hands_500': ('Regular', 'Play 500 hands.'),
    'high_roller': ('High roller', 'Reach 5000 chips.'),
    'iron_stomach': ('Iron stomach', 'Bust 25 times.'),
    'magnate': ('Magnate', 'Reach 25000 chips.'),
    'profitable': ('Clean books', 'Finish in profit after at least 50 hands.'),
    'split_master': ('Split specialist', 'Make 10 splits.'),
    'streak_10': ('Unstoppable', 'Win 10 hands in a row.'),
    'streak_15': ('Legendary streak', 'Win 15 hands in a row.'),
    'streak_5': ('On a roll', 'Win 5 hands in a row.'),
    'whale': ('Whale', 'Reach 10000 chips.'),
}
_ACHIEVEMENTS_FR: dict[str, tuple[str, str]] = {
    'bj_10': ('As de la maison', 'Obtenez 10 Blackjacks.'),
    'bj_25': ('Roi du Blackjack', 'Obtenez 25 Blackjacks.'),
    'busts_50': ('Increvable', 'Sautez (bust) 50 fois.'),
    'comeback': ('Retour gagnant', 'Reprenez le dessus après avoir frôlé la ruine.'),
    'first_bj': ('Blackjack !', 'Obtenez votre premier Blackjack naturel.'),
    'first_push': ('Égalité', 'Faites égalité avec le croupier pour la première fois.'),
    'first_split': ('Diviser pour mieux régner', 'Faites votre premier split.'),
    'first_surrender': ('Retraite tactique', 'Abandonnez pour la première fois.'),
    'first_win': ('Première victoire', 'Gagnez votre première main.'),
    'hands_100': ('Cent mains', 'Jouez 100 mains.'),
    'hands_1000': ('Mille mains', 'Jouez 1000 mains.'),
    'hands_500': ('Habitué', 'Jouez 500 mains.'),
    'high_roller': ('Gros joueur', 'Atteignez 5000 jetons.'),
    'iron_stomach': ("Estomac d'acier", 'Sautez (bust) 25 fois.'),
    'magnate': ('Magnat', 'Atteignez 25000 jetons.'),
    'profitable': ('Bilan positif', 'Terminez en profit après au moins 50 mains.'),
    'split_master': ('Spécialiste du split', 'Faites 10 splits.'),
    'streak_10': ('Imparable', "Enchaînez 10 victoires d'affilée."),
    'streak_15': ('Série légendaire', "Enchaînez 15 victoires d'affilée."),
    'streak_5': ('Sur une lancée', "Enchaînez 5 victoires d'affilée."),
    'whale': ('Baleine', 'Atteignez 10000 jetons.'),
}
_ACHIEVEMENTS_PT: dict[str, tuple[str, str]] = {
    'bj_10': ('Ás da casa', 'Consegue 10 Blackjacks.'),
    'bj_25': ('Rei do Blackjack', 'Consegue 25 Blackjacks.'),
    'busts_50': ('À prova de balas', 'Rebenta (bust) 50 vezes.'),
    'comeback': ('Reviravolta', 'Recupera depois de quase teres ido à falência.'),
    'first_bj': ('Blackjack!', 'Consegue o teu primeiro Blackjack natural.'),
    'first_push': ('Empate', 'Empata com o crupiê pela primeira vez.'),
    'first_split': ('Divide e vencerás', 'Faz o teu primeiro split.'),
    'first_surrender': ('Retirada tática', 'Rende-te pela primeira vez.'),
    'first_win': ('Primeira vitória', 'Ganha a tua primeira mão.'),
    'hands_100': ('Cem mãos', 'Joga 100 mãos.'),
    'hands_1000': ('Mil mãos', 'Joga 1000 mãos.'),
    'hands_500': ('Habitual', 'Joga 500 mãos.'),
    'high_roller': ('Grande apostador', 'Alcança 5000 fichas.'),
    'iron_stomach': ('Estômago de ferro', 'Rebenta (bust) 25 vezes.'),
    'magnate': ('Magnata', 'Alcança 25000 fichas.'),
    'profitable': ('Contas certas', 'Termina em positivo depois de pelo menos 50 mãos.'),
    'split_master': ('Especialista em splits', 'Faz 10 splits.'),
    'streak_10': ('Imparável', 'Encadeia 10 vitórias seguidas.'),
    'streak_15': ('Sequência lendária', 'Encadeia 15 vitórias seguidas.'),
    'streak_5': ('Em sequência', 'Encadeia 5 vitórias seguidas.'),
    'whale': ('Baleia', 'Alcança 10000 fichas.'),
}
_ACHIEVEMENTS_DE: dict[str, tuple[str, str]] = {
    'bj_10': ('Hausass', 'Hol dir 10 Blackjacks.'),
    'bj_25': ('Blackjack-König', 'Hol dir 25 Blackjacks.'),
    'busts_50': ('Kugelsicher', 'Überkaufe dich 50 Mal.'),
    'comeback': ('Comeback', 'Erhole dich, nachdem du fast pleite warst.'),
    'first_bj': ('Blackjack!', 'Hol dir deinen ersten natürlichen Blackjack.'),
    'first_push': ('Unentschieden', 'Spiele zum ersten Mal unentschieden gegen den Dealer.'),
    'first_split': ('Teile und herrsche', 'Mach deinen ersten Split.'),
    'first_surrender': ('Taktischer Rückzug', 'Gib zum ersten Mal auf.'),
    'first_win': ('Erster Sieg', 'Gewinne deine erste Hand.'),
    'hands_100': ('Hundert Hände', 'Spiele 100 Hände.'),
    'hands_1000': ('Tausend Hände', 'Spiele 1000 Hände.'),
    'hands_500': ('Stammgast', 'Spiele 500 Hände.'),
    'high_roller': ('High Roller', 'Erreiche 5000 Chips.'),
    'iron_stomach': ('Eiserner Magen', 'Überkaufe dich 25 Mal.'),
    'magnate': ('Magnat', 'Erreiche 25000 Chips.'),
    'profitable': ('Reiner Gewinn', 'Beende nach mindestens 50 gespielten Händen im Plus.'),
    'split_master': ('Split-Experte', 'Mach 10 Splits.'),
    'streak_10': ('Unaufhaltsam', 'Gewinne 10 Hände in Folge.'),
    'streak_15': ('Legendäre Serie', 'Gewinne 15 Hände in Folge.'),
    'streak_5': ('In Fahrt', 'Gewinne 5 Hände in Folge.'),
    'whale': ('Wal', 'Erreiche 10000 Chips.'),
}
_ACHIEVEMENT_TABLES: dict[str, dict[str, tuple[str, str]]] = {
    "en": _ACHIEVEMENTS_EN, "fr": _ACHIEVEMENTS_FR,
    "pt": _ACHIEVEMENTS_PT, "de": _ACHIEVEMENTS_DE,
}

# engine/challenges.py -- id -> (nombre, descripción) por idioma
_CHALLENGES_EN: dict[str, tuple[str, str]] = {
    'contrarreloj': ('Against the Clock', 'Finish exactly 15 hands with more chips than you started with.'),
    'meta_rapida': ('Quick Target', 'Reach $1500 in chips before 20 hands run out.'),
    'racha_hierro': ('Iron Streak', "Win 5 hands in a row without losing a single one along the way. One slip and it's over."),
    'superviviente': ('Survivor', 'Play 25 hands in a row without running out of chips. You start short on cash -- watch your bets.'),
}
_CHALLENGES_FR: dict[str, tuple[str, str]] = {
    'contrarreloj': ('Contre la Montre', "Terminez exactement 15 mains avec plus de jetons que vous n'en aviez au départ."),
    'meta_rapida': ('Objectif Rapide', 'Atteignez 1500 $ de jetons avant la fin des 20 mains.'),
    'racha_hierro': ('Série de Fer', "Remportez 5 victoires d'affilée sans perdre une seule main en chemin. Un seul faux pas et c'est terminé."),
    'superviviente': ('Survivant', "Jouez 25 mains d'affilée sans manquer de jetons. Vous commencez avec peu d'argent -- attention à vos mises."),
}
_CHALLENGES_PT: dict[str, tuple[str, str]] = {
    'contrarreloj': ('Contrarrelógio', 'Termina exatamente 15 mãos com mais fichas do que aquelas com que começaste.'),
    'meta_rapida': ('Meta Rápida', 'Chega a $1500 em fichas antes que as 20 mãos se esgotem.'),
    'racha_hierro': ('Sequência de Ferro', 'Consegue 5 vitórias seguidas sem perderes uma única mão pelo caminho. Um só deslize e acaba tudo.'),
    'superviviente': ('Sobrevivente', 'Joga 25 mãos seguidas sem ficares sem fichas. Começas com pouco dinheiro -- cuidado com as apostas.'),
}
_CHALLENGES_DE: dict[str, tuple[str, str]] = {
    'contrarreloj': ('Gegen die Uhr', 'Beende genau 15 Hände mit mehr Chips, als du gestartet bist.'),
    'meta_rapida': ('Schnelles Ziel', 'Erreiche $1500 in Chips, bevor 20 Hände vorbei sind.'),
    'racha_hierro': ('Eiserne Serie', 'Gewinne 5 Hände in Folge, ohne auch nur eine einzige zu verlieren. Ein einziger Ausrutscher und es ist vorbei.'),
    'superviviente': ('Überlebenskünstler', 'Spiele 25 Hände in Folge, ohne dass dir die Chips ausgehen. Du startest mit wenig Geld -- pass auf deine Einsätze auf.'),
}
_CHALLENGE_TABLES: dict[str, dict[str, tuple[str, str]]] = {
    "en": _CHALLENGES_EN, "fr": _CHALLENGES_FR,
    "pt": _CHALLENGES_PT, "de": _CHALLENGES_DE,
}


def achievement_text(ach) -> tuple[str, str]:
    """(nombre, descripción) del logro en el idioma activo; si falta la
    traducción, cae al español (nunca se queda en blanco)."""
    table = _ACHIEVEMENT_TABLES.get(getattr(cfg, "LANGUAGE", "es"))
    if table:
        pair = table.get(ach.id)
        if pair:
            return pair
    return ach.name, ach.description


def challenge_text(ch) -> tuple[str, str]:
    """(nombre, descripción) del desafío en el idioma activo."""
    table = _CHALLENGE_TABLES.get(getattr(cfg, "LANGUAGE", "es"))
    if table:
        pair = table.get(ch.id)
        if pair:
            return pair
    return ch.name, ch.description


# config/rules_presets.py -- nombre interno (clave de PRESETS, no se
# toca) -> nombre a mostrar por idioma. Los que no aparecen aquí (Vegas
# Strip, Atlantic City, European, Single Deck, Downtown Vegas, Macau,
# High Roller) son ya nombres propios en inglés y se muestran igual en
# todos los idiomas.
_PRESET_NAMES_EN: dict[str, str] = {
    'Personalizado': 'Custom',
    'Reglas de Casa': 'House Rules',
}
_PRESET_NAMES_FR: dict[str, str] = {
    'Personalizado': 'Personnalisé',
    'Reglas de Casa': 'Règles de la Maison',
}
_PRESET_NAMES_PT: dict[str, str] = {
    'Personalizado': 'Personalizado',
    'Reglas de Casa': 'Regras da Casa',
}
_PRESET_NAMES_DE: dict[str, str] = {
    'Personalizado': 'Benutzerdefiniert',
    'Reglas de Casa': 'Haus-Regeln',
}
_PRESET_TABLES: dict[str, dict[str, str]] = {
    "en": _PRESET_NAMES_EN, "fr": _PRESET_NAMES_FR,
    "pt": _PRESET_NAMES_PT, "de": _PRESET_NAMES_DE,
}


def preset_label(name: str) -> str:
    table = _PRESET_TABLES.get(getattr(cfg, "LANGUAGE", "es"))
    if table:
        return table.get(name, name)
    return name


# engine/side_bets.py -- SideBetOutcome.label es un identificador propio
# en español (también aparece como CLAVE en PERFECT_PAIRS_PAYOUTS /
# TWENTYONE_PLUS_THREE_PAYOUTS, así que nunca se toca) -> traducción
# solo para mostrar en pantalla, por idioma.
_SIDE_BET_LABELS_EN: dict[str, str] = {
    'Color': 'Flush',
    'Escalera': 'Straight',
    'Escalera de color': 'Straight flush',
    'Pareja de color': 'Colored pair',
    'Pareja mixta': 'Mixed pair',
    'Pareja perfecta': 'Perfect pair',
    'Sin pareja': 'No pair',
    'Sin premio': 'No win',
    'Trío': 'Three of a kind',
    'Trío de color': 'Suited trips',
}
_SIDE_BET_LABELS_FR: dict[str, str] = {
    'Color': 'Couleur',
    'Escalera': 'Quinte',
    'Escalera de color': 'Quinte flush',
    'Pareja de color': 'Paire colorée',
    'Pareja mixta': 'Paire mixte',
    'Pareja perfecta': 'Paire parfaite',
    'Sin pareja': 'Aucune paire',
    'Sin premio': 'Aucun gain',
    'Trío': 'Brelan',
    'Trío de color': 'Brelan de couleur',
}
_SIDE_BET_LABELS_PT: dict[str, str] = {
    'Color': 'Cor',
    'Escalera': 'Sequência',
    'Escalera de color': 'Sequência de cor',
    'Pareja de color': 'Par da mesma cor',
    'Pareja mixta': 'Par misto',
    'Pareja perfecta': 'Par perfeito',
    'Sin pareja': 'Sem par',
    'Sin premio': 'Sem prémio',
    'Trío': 'Trinca',
    'Trío de color': 'Trinca do mesmo naipe',
}
_SIDE_BET_LABELS_DE: dict[str, str] = {
    'Color': 'Flush',
    'Escalera': 'Straße',
    'Escalera de color': 'Straight Flush',
    'Pareja de color': 'Farbiges Paar',
    'Pareja mixta': 'Gemischtes Paar',
    'Pareja perfecta': 'Perfektes Paar',
    'Sin pareja': 'Kein Paar',
    'Sin premio': 'Kein Gewinn',
    'Trío': 'Drilling',
    'Trío de color': 'Farbdrilling',
}
_SIDE_BET_TABLES: dict[str, dict[str, str]] = {
    "en": _SIDE_BET_LABELS_EN, "fr": _SIDE_BET_LABELS_FR,
    "pt": _SIDE_BET_LABELS_PT, "de": _SIDE_BET_LABELS_DE,
}


def side_bet_label(label: str) -> str:
    table = _SIDE_BET_TABLES.get(getattr(cfg, "LANGUAGE", "es"))
    if table:
        return table.get(label, label)
    return label


# config/settings.py -- TABLE_THEMES / CARD_BACK_THEMES: clave interna
# (no se toca, se usa para persistir en app_settings.json) -> etiqueta
# a mostrar por idioma.
_TABLE_THEME_LABELS_EN: dict[str, str] = {
    'burgundy': 'Burgundy',
    'classic_green': 'Classic green',
    'midnight': 'Midnight black',
    'royal_blue': 'Royal blue',
}
_TABLE_THEME_LABELS_FR: dict[str, str] = {
    'burgundy': 'Bordeaux',
    'classic_green': 'Vert classique',
    'midnight': 'Noir de minuit',
    'royal_blue': 'Bleu royal',
}
_TABLE_THEME_LABELS_PT: dict[str, str] = {
    'burgundy': 'Vinho',
    'classic_green': 'Verde clássico',
    'midnight': 'Preto meia-noite',
    'royal_blue': 'Azul real',
}
_TABLE_THEME_LABELS_DE: dict[str, str] = {
    'burgundy': 'Bordeaux',
    'classic_green': 'Klassisches Grün',
    'midnight': 'Mitternachtsschwarz',
    'royal_blue': 'Königsblau',
}
_TABLE_THEME_TABLES: dict[str, dict[str, str]] = {
    "en": _TABLE_THEME_LABELS_EN, "fr": _TABLE_THEME_LABELS_FR,
    "pt": _TABLE_THEME_LABELS_PT, "de": _TABLE_THEME_LABELS_DE,
}
_CARD_BACK_LABELS_EN: dict[str, str] = {
    'blue_royal': 'Royal blue',
    'green_gold': 'Green & gold',
    'red_classic': 'Classic red',
}
_CARD_BACK_LABELS_FR: dict[str, str] = {
    'blue_royal': 'Bleu royal',
    'green_gold': 'Vert et or',
    'red_classic': 'Rouge classique',
}
_CARD_BACK_LABELS_PT: dict[str, str] = {
    'blue_royal': 'Azul real',
    'green_gold': 'Verde e dourado',
    'red_classic': 'Vermelho clássico',
}
_CARD_BACK_LABELS_DE: dict[str, str] = {
    'blue_royal': 'Königsblau',
    'green_gold': 'Grün und Gold',
    'red_classic': 'Klassisches Rot',
}
_CARD_BACK_TABLES: dict[str, dict[str, str]] = {
    "en": _CARD_BACK_LABELS_EN, "fr": _CARD_BACK_LABELS_FR,
    "pt": _CARD_BACK_LABELS_PT, "de": _CARD_BACK_LABELS_DE,
}


def table_theme_label(key: str, fallback_es: str) -> str:
    table = _TABLE_THEME_TABLES.get(getattr(cfg, "LANGUAGE", "es"))
    if table:
        return table.get(key, fallback_es)
    return fallback_es


def card_back_label(key: str, fallback_es: str) -> str:
    table = _CARD_BACK_TABLES.get(getattr(cfg, "LANGUAGE", "es"))
    if table:
        return table.get(key, fallback_es)
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


# ------------------------------------------------------------------
# Fase 27: francés, portugués (Portugal) y alemán -- textos simples
# (equivalentes a todas las llamadas _add(...) de arriba). Se cargan
# en bloque aparte para no tener que tocar ninguna de esas líneas
# es/en existentes ni arriesgarse a desincronizar las claves; t() ya
# hace fallback a español si algún día faltase alguna futura clave
# nueva en estos tres diccionarios.
# ------------------------------------------------------------------
_STRINGS_FR: dict[str, str] = {
    'animations.achievement_for_player': 'SUCCÈS DE {name}',
    'animations.achievement_unlocked': 'SUCCÈS DÉBLOQUÉ',
    'challenge.progress_chips': '${chips} / ${target}',
    'challenge.progress_hand': 'Main {hand} / {limit}',
    'challenge.progress_net': 'Net : {net:+.0f}',
    'challenge.progress_streak': 'Série {cur} / {target}',
    'challenge_select.back_button': 'Retour',
    'challenge_select.detail_bet_range': 'Mise : ${min} - ${max}',
    'challenge_select.detail_fail_on_loss': 'Toute défaite, égalité ou abandon met fin au défi',
    'challenge_select.detail_hand_limit': 'Limite de mains : {limit}',
    'challenge_select.detail_require_profit': "Objectif : terminer avec plus de jetons qu'au départ",
    'challenge_select.detail_starting_chips': 'Jetons de départ : ${chips}',
    'challenge_select.detail_target_chips': 'Objectif : atteindre ${target} en jetons',
    'challenge_select.detail_target_streak': 'Objectif : une série de {streak} victoires consécutives',
    'challenge_select.hint': 'Flèches pour se déplacer · Entrée/Commencer confirme · Échap/Retour annule',
    'challenge_select.item_facts': '{limit} mains · ${chips} de départ',
    'challenge_select.start_button': 'Commencer le défi',
    'challenge_select.subtitle': 'Des parties courtes avec un objectif précis -- idéal pour une session rapide',
    'challenge_select.title': 'DÉFIS',
    'chipstack.undo_hint': 'Clic droit -> reprendre le dernier jeton',
    'counter.cold': 'Froid ❄️',
    'counter.hot': 'Chaud 🔥',
    'counter.neutral': 'Neutre ➖',
    'counter.very_cold': 'Très froid 🥶',
    'counter.very_hot': 'Très chaud ! 🌋',
    'counter.warm': 'Tiède 🌡️',
    'engine.action_unavailable': 'Action « {action} » indisponible pour le moment.',
    'engine.dealer_has_blackjack': 'Le croupier a Blackjack !',
    'engine.even_money_paid': '{name} : Even Money payé.',
    'engine.invalid_bet': 'Mise invalide. Min={min}, Max={max}',
    'engine.invalid_side_bet': 'Mise latérale invalide. Max={max}',
    'engine.not_enough_chips': "Vous n'avez pas assez de jetons.",
    'engine.out_of_chips': "Vous n'avez plus de jetons ! Partie terminée.",
    'engine.reshuffling': 'Rebattage du sabot...',
    'history.back_button': 'Retour',
    'history.chip_evolution_label': 'Évolution des jetons (dernières {n} mains)',
    'history.col_bet': 'Mise',
    'history.col_casino': 'Casino',
    'history.col_chips': 'Jetons',
    'history.col_date': 'Date',
    'history.col_net': 'Net',
    'history.col_result': 'Résultat',
    'history.default_player_name': 'Joueur',
    'history.empty_state': "Aucune main jouée pour l'instant avec ce profil.",
    'history.hint_esc_exit': 'Échap/Retour pour quitter',
    'history.hint_page_arrows': 'Flèches pour changer de page',
    'history.hint_tab_switch': 'Tab pour changer de profil',
    'history.pagination_label': 'Page {page} / {total_pages}  ·  {total} mains au total',
    'history.result_blackjack_win': 'Blackjack !',
    'history.result_dealer_bust': 'Le croupier a sauté',
    'history.result_loss': 'Vous avez perdu',
    'history.result_push': 'Égalité',
    'history.result_surrender': 'Abandon',
    'history.result_win': 'Vous avez gagné',
    'history.title_for_profile': 'Historique de {name}',
    'hud.achievements_title': 'Succès  ({n}/{total})',
    'hud.action_double_or_hit': 'Double (sinon Hit)',
    'hud.action_double_or_stand': 'Double (sinon Stand)',
    'hud.action_split_or_hit': 'Split (sinon Hit)',
    'hud.action_surrender_or_hit': 'Surrender (sinon Hit)',
    'hud.action_surrender_or_split': 'Surrender (sinon Split)',
    'hud.action_surrender_or_stand': 'Surrender (sinon Stand)',
    'hud.category_blackjack': 'Blackjack',
    'hud.category_bust': 'Sauté',
    'hud.category_count_label': '{label} : {n}',
    'hud.category_loss': 'Défaite',
    'hud.category_push': 'Égalité',
    'hud.category_surrender': 'Abandon',
    'hud.category_win': 'Victoire',
    'hud.challenge_hands_progress': 'Main {played}/{limit}',
    'hud.result_distribution_title': 'Répartition des résultats',
    'hud.stat_best_streak': 'Meilleure série : +{n}',
    'hud.stat_blackjacks': 'Blackjacks : {n}',
    'hud.stat_busts': 'Sautés :    {n}',
    'hud.stat_chips': 'Jetons :  {chips}',
    'hud.stat_hands': 'Mains :   {n}',
    'hud.stat_net': 'Net :    {net:+.0f}',
    'hud.stat_player': 'Joueur : {name}',
    'hud.stat_roi': 'ROI :     {roi:+.1%}',
    'hud.stat_winrate': 'Taux de victoire : {pct:.1%}',
    'hud.stat_wlp': 'V / D / N : {w} / {l} / {p}',
    'hud.strategy_hint': 'Stratégie : {label}',
    'hud.streak_sparkline_title': 'Série de la session (actuelle : {current:+d})',
    'hud.training_badge': 'Entraînement : {correct}/{total} ({pct:.0f}%)',
    'insurance.no': 'Non',
    'insurance.yes': 'Assurance (Oui)',
    'leaderboard.back_button': 'Retour',
    'leaderboard.col_achievements': 'Succès',
    'leaderboard.col_best_streak': 'Meilleure série',
    'leaderboard.col_blackjacks': 'Blackjacks',
    'leaderboard.col_chips': 'Jetons',
    'leaderboard.col_hands': 'Mains',
    'leaderboard.col_name': 'Profil',
    'leaderboard.col_rank': '#',
    'leaderboard.col_win_pct': '% Victoires',
    'leaderboard.empty_state': "Il n'y a pas encore de profils à comparer.",
    'leaderboard.hint_esc_exit': 'Échap/Retour pour quitter',
    'leaderboard.sort_hint': 'Cliquez sur une colonne pour trier',
    'leaderboard.title': 'Classement des profils',
    'menu.back_button': 'Retour',
    'menu.challenges_button': 'Défis',
    'menu.custom_hint': 'Appuyez sur Entrée ou JOUER pour définir vos propres règles',
    'menu.custom_option': 'Personnalisé...',
    'menu.dealer_hit_h17': 'Tire (H17)',
    'menu.dealer_stand_s17': 'Reste (S17)',
    'menu.double_9_10_11': 'Seulement 9, 10 ou 11',
    'menu.double_any_two': "N'importe quelles 2 cartes",
    'menu.field.blackjack_payout': 'Paiement du Blackjack',
    'menu.field.dealer_rule': 'Croupier sur 17 souple',
    'menu.field.double_after_split': 'Doubler après split (DAS)',
    'menu.field.double_rule': 'Doubler autorisé sur',
    'menu.field.even_money_allowed': 'Even Money',
    'menu.field.five_card_charlie': 'Five Card Charlie',
    'menu.field.hit_split_aces': 'Tirer après split des As',
    'menu.field.insurance_allowed': 'Assurance autorisée',
    'menu.field.max_bet': 'Mise maximale',
    'menu.field.max_splits': 'Splits maximum',
    'menu.field.min_bet': 'Mise minimale',
    'menu.field.num_decks': 'Jeux de cartes',
    'menu.field.original_bets_only': 'OBBO (BJ du croupier)',
    'menu.field.penetration': 'Pénétration du sabot',
    'menu.field.perfect_pairs_allowed': 'Mise latérale : Paires Parfaites',
    'menu.field.resplit_aces': 'Re-split des As',
    'menu.field.side_bet_max': 'Limite de mise latérale',
    'menu.field.starting_chips': 'Jetons de départ',
    'menu.field.surrender_rule': 'Abandon (Surrender)',
    'menu.field.twentyone_plus_three_allowed': 'Mise latérale : 21+3',
    'menu.hint_base': 'Flèches haut/bas pour sélectionner · Entrée pour jouer',
    'menu.hint_history_suffix': ' · H : historique',
    'menu.history_button': 'Historique',
    'menu.max_splits_fmt': "{v} (jusqu'à {n} mains)",
    'menu.no': 'Non',
    'menu.play_button': 'JOUER',
    'menu.player_label': 'Joueur : {name}',
    'menu.reset_button': 'Réinitialiser',
    'menu.rules_editor_title': 'RÈGLES PERSONNALISÉES',
    'menu.rules_hint': 'Flèches pour se déplacer et modifier les valeurs · Entrée/JOUER confirme · Échap/Retour annule',
    'menu.select_casino': 'Sélectionnez un casino :',
    'menu.settings_button': 'Paramètres',
    'menu.surrender_early': 'Précoce',
    'menu.surrender_late': 'Tardif',
    'menu.surrender_none': 'Non autorisé',
    'menu.yes': 'Oui',
    'profile.add_player_button': '+  Ajouter un joueur',
    'profile.avatar_label': 'Avatar :',
    'profile.cancel_button': 'Annuler',
    'profile.chips_hands_info': '{chips:.0f} jetons · {hands} mains jouées',
    'profile.confirm_delete': 'Supprimer ? Cliquez à nouveau pour confirmer',
    'profile.create_button': 'Créer',
    'profile.create_hint': "Flèches pour choisir l'avatar · Entrée pour créer · Échap pour revenir",
    'profile.create_title': 'Nouveau profil',
    'profile.error_empty_name': 'Saisissez un nom pour le profil.',
    'profile.leaderboard_button': 'Classement',
    'profile.list_hint': "Cliquez sur un profil pour continuer · icône liste : voir l'historique · icône corbeille : supprimer · N : nouveau profil · Classement : comparer les profils",
    'profile.max_players_note': 'Maximum 3 joueurs à la table',
    'profile.name_label': 'Nom :',
    'profile.new_profile_button': '+  Nouveau profil',
    'profile.play_button': 'Jouer',
    'profile.play_solo_button': 'Jouer en solo',
    'profile.seat_number': 'Siège {n}',
    'profile.seats_hint_add': ' · A pour ajouter un autre joueur',
    'profile.seats_hint_play': 'Entrée pour jouer',
    'profile.seats_title': 'Joueurs à la table',
    'profile.subtitle_default': 'Profils locaux — sans mot de passe, chacun avec son propre historique',
    'profile.subtitle_seat': "Choisissez qui s'installe au prochain siège",
    'profile.title_default': 'Qui joue ?',
    'profile_store.duplicate_name': 'Un profil nommé « {name} » existe déjà.',
    'profile_store.empty_name': 'Le nom ne peut pas être vide.',
    'renderer.action_double': 'Doubler',
    'renderer.action_hit': 'Tirer',
    'renderer.action_split': 'Séparer',
    'renderer.action_stand': 'Rester',
    'renderer.action_surrender': 'Abandonner',
    'renderer.betting_hint': 'Cliquez sur les jetons pour miser · Entrée pour distribuer',
    'renderer.betting_turn': 'Tour de mise : {name}',
    'renderer.blackjack_bang': 'Blackjack !',
    'renderer.challenge_lost_title': 'DÉFI ÉCHOUÉ',
    'renderer.challenge_preset_label': 'Défi : {name}',
    'renderer.challenge_won_title': 'DÉFI RÉUSSI !',
    'renderer.continue_hint': 'Cliquez ou Entrée pour continuer',
    'renderer.deal_button': 'DISTRIBUER',
    'renderer.dealer_blackjack': 'Le croupier a Blackjack',
    'renderer.dealer_busts': 'Le croupier saute !',
    'renderer.dealer_hits': 'Le croupier tire une carte...',
    'renderer.dealer_reveals': 'Le croupier révèle sa carte...',
    'renderer.dealer_shows_ace': 'Le croupier montre un As — Assurance ?',
    'renderer.dealer_stands': 'Le croupier reste sur {value}',
    'renderer.dealing_to': 'Distribution à {name}...',
    'renderer.double_and_bust': '{name} double et saute ({value})',
    'renderer.double_result': '{name} double : {value}',
    'renderer.esc_to_menu': 'ÉCHAP -> Menu principal',
    'renderer.even_money_or_insurance': 'Even Money ou Assurance ?',
    'renderer.final_chips_net_stat': 'Jetons finaux : {chips}   Net : {net:+.0f}',
    'renderer.game_over_title': 'GAME OVER',
    'renderer.hand_n_label': 'Main {n} : ',
    'renderer.hands_played_stat': 'Mains jouées : {n}',
    'renderer.keybinds_hint': 'F1 : Indices  F2 : Compteur  F3 : Stats  F4 : Succès  F5 : Entraînement  M : Musique  ÉCHAP : Menu',
    'renderer.min_bet_warning': 'Mise minimale : ${amount}',
    'renderer.n_hands': '{n} mains',
    'renderer.natural_blackjack': '{name} a Blackjack !',
    'renderer.net_roi_stat': 'Net : {net:+.0f}   ROI : {roi:+.1%}',
    'renderer.player_n_fallback': 'Joueur {n}',
    'renderer.rebet_button': 'Remiser ${amount}',
    'renderer.reshuffling': 'Rebattage',
    'renderer.result_blackjack': 'BLACKJACK !',
    'renderer.result_dealer_bust': 'LE CROUPIER A SAUTÉ',
    'renderer.result_loss': 'VOUS AVEZ PERDU',
    'renderer.result_push': 'ÉGALITÉ',
    'renderer.result_surrender': 'ABANDON',
    'renderer.result_win': 'VOUS AVEZ GAGNÉ',
    'renderer.round_result_title': 'RÉSULTAT DE LA MANCHE',
    'renderer.seat_blackjack': 'BLACKJACK !',
    'renderer.seat_doubles': 'DOUBLE',
    'renderer.seat_split_aces': 'AS',
    'renderer.shoe_info': 'Sabot : {remaining}/{total}',
    'renderer.sidebet_perfect_pairs': 'Paires Parfaites',
    'renderer.split_aces_result': '{name} sépare les As : {v1} et {v2}',
    'renderer.status_betting': 'mise en cours',
    'renderer.status_bust': 'sauté ({value})',
    'renderer.status_dealing': 'distribution',
    'renderer.status_hand_value': 'main : {value}',
    'renderer.status_in_game': 'en jeu',
    'renderer.status_insurance': 'assurance',
    'renderer.status_playing': 'en cours',
    'renderer.status_stood': 'reste ({value})',
    'renderer.status_waiting': 'en attente',
    'renderer.title_add_seat': "Qui d'autre s'installe ?",
    'renderer.total_label': 'Total : {sign}{amount}',
    'renderer.training_correct': 'Correct !',
    'renderer.training_mode_toggle': 'Mode entraînement {state}',
    'renderer.training_off': 'désactivé',
    'renderer.training_on': 'activé',
    'renderer.training_should_have': 'Stratégie de base : {label}',
    'renderer.wlp_stat': 'V / D / N :  {w} / {l} / {p}',
    'replay.back_button': 'Retour',
    'replay.dealer_label_empty': 'CROUPIER',
    'replay.dealer_label_value': 'CROUPIER  {value}',
    'replay.exit_hint': 'Échap/Retour pour quitter',
    'replay.info_bar': '{date}   ·   {preset}   ·   Mise : ${bet:.0f}',
    'replay.no_data': 'Aucune donnée de relecture enregistrée pour cette main.',
    'replay.parse_error': 'Impossible de lire la relecture de cette main.',
    'replay.player_label_empty': 'VOTRE MAIN',
    'replay.player_label_value': 'VOTRE MAIN  {value}{tags}',
    'replay.tag_doubled': 'doublée',
    'replay.tag_surrendered': 'abandonnée',
    'settings.audio_section': 'Audio',
    'settings.card_back_section': 'Dos de carte',
    'settings.hint': 'Cliquez pour appliquer instantanément · faites glisser les curseurs de volume · Échap/Retour pour quitter',
    'settings.language_section': 'Langue',
    'settings.music_label': 'Musique',
    'settings.muted': 'Muet',
    'settings.sfx_label': 'Effets sonores',
    'settings.table_section': 'Table',
    'sidebets.perfect_pairs_label': 'Paires Parfaites',
    'sidebets.title': 'Mises latérales (optionnel)',
    'table.bet_label': 'Mise : {bet}',
    'table.dealer_label': 'CROUPIER  {value}',
    'table.hand_label': 'VOTRE MAIN  {value}',
}
_STRINGS_PT: dict[str, str] = {
    'animations.achievement_for_player': 'CONQUISTA DE {name}',
    'animations.achievement_unlocked': 'CONQUISTA DESBLOQUEADA',
    'challenge.progress_chips': '${chips} / ${target}',
    'challenge.progress_hand': 'Mão {hand} / {limit}',
    'challenge.progress_net': 'Líquido: {net:+.0f}',
    'challenge.progress_streak': 'Sequência {cur} / {target}',
    'challenge_select.back_button': 'Voltar',
    'challenge_select.detail_bet_range': 'Aposta: ${min} - ${max}',
    'challenge_select.detail_fail_on_loss': 'Qualquer derrota, empate ou rendição termina o desafio',
    'challenge_select.detail_hand_limit': 'Limite de mãos: {limit}',
    'challenge_select.detail_require_profit': 'Objetivo: terminar com mais fichas do que aquelas com que começaste',
    'challenge_select.detail_starting_chips': 'Fichas iniciais: ${chips}',
    'challenge_select.detail_target_chips': 'Objetivo: chegar a ${target} em fichas',
    'challenge_select.detail_target_streak': 'Objetivo: sequência de {streak} vitórias seguidas',
    'challenge_select.hint': 'Setas para mover · Enter/Começar confirma · Esc/Voltar cancela',
    'challenge_select.item_facts': '{limit} mãos · ${chips} iniciais',
    'challenge_select.start_button': 'Começar Desafio',
    'challenge_select.subtitle': 'Partidas curtas com um objetivo concreto -- ideal para uma sessão rápida',
    'challenge_select.title': 'DESAFIOS',
    'chipstack.undo_hint': 'Clique direito -> devolver última ficha',
    'counter.cold': 'Frio ❄️',
    'counter.hot': 'Quente 🔥',
    'counter.neutral': 'Neutro ➖',
    'counter.very_cold': 'Muito frio 🥶',
    'counter.very_hot': 'Muito quente! 🌋',
    'counter.warm': 'Morno 🌡️',
    'engine.action_unavailable': "Ação '{action}' não disponível agora.",
    'engine.dealer_has_blackjack': 'O crupiê tem Blackjack!',
    'engine.even_money_paid': '{name}: Even Money pago.',
    'engine.invalid_bet': 'Aposta inválida. Min={min}, Max={max}',
    'engine.invalid_side_bet': 'Aposta lateral inválida. Max={max}',
    'engine.not_enough_chips': 'Não tens fichas suficientes.',
    'engine.out_of_chips': 'Ficaste sem fichas! Partida terminada.',
    'engine.reshuffling': 'A baralhar o sapato...',
    'history.back_button': 'Voltar',
    'history.chip_evolution_label': 'Evolução de fichas (últimas {n} mãos)',
    'history.col_bet': 'Aposta',
    'history.col_casino': 'Casino',
    'history.col_chips': 'Fichas',
    'history.col_date': 'Data',
    'history.col_net': 'Líquido',
    'history.col_result': 'Resultado',
    'history.default_player_name': 'Jogador',
    'history.empty_state': 'Ainda não há mãos jogadas com este perfil.',
    'history.hint_esc_exit': 'Esc/Voltar para sair',
    'history.hint_page_arrows': 'Setas para mudar de página',
    'history.hint_tab_switch': 'Tab para mudar de perfil',
    'history.pagination_label': 'Página {page} / {total_pages}  ·  {total} mãos no total',
    'history.result_blackjack_win': 'Blackjack!',
    'history.result_dealer_bust': 'Crupiê rebentou',
    'history.result_loss': 'Perdeste',
    'history.result_push': 'Empate',
    'history.result_surrender': 'Rendição',
    'history.result_win': 'Ganhaste',
    'history.title_for_profile': 'Histórico de {name}',
    'hud.achievements_title': 'Conquistas  ({n}/{total})',
    'hud.action_double_or_hit': 'Double (senão, Hit)',
    'hud.action_double_or_stand': 'Double (senão, Stand)',
    'hud.action_split_or_hit': 'Split (senão, Hit)',
    'hud.action_surrender_or_hit': 'Surrender (senão, Hit)',
    'hud.action_surrender_or_split': 'Surrender (senão, Split)',
    'hud.action_surrender_or_stand': 'Surrender (senão, Stand)',
    'hud.category_blackjack': 'Blackjack',
    'hud.category_bust': 'Rebentada',
    'hud.category_count_label': '{label}: {n}',
    'hud.category_loss': 'Derrota',
    'hud.category_push': 'Empate',
    'hud.category_surrender': 'Rendição',
    'hud.category_win': 'Vitória',
    'hud.challenge_hands_progress': 'Mão {played}/{limit}',
    'hud.result_distribution_title': 'Distribuição de resultados',
    'hud.stat_best_streak': 'Melhor sequência: +{n}',
    'hud.stat_blackjacks': 'Blackjacks: {n}',
    'hud.stat_busts': 'Rebentadas:  {n}',
    'hud.stat_chips': 'Fichas:  {chips}',
    'hud.stat_hands': 'Mãos:    {n}',
    'hud.stat_net': 'Líquido: {net:+.0f}',
    'hud.stat_player': 'Jogador: {name}',
    'hud.stat_roi': 'ROI:     {roi:+.1%}',
    'hud.stat_winrate': 'Taxa de vitórias: {pct:.1%}',
    'hud.stat_wlp': 'W / L / P: {w} / {l} / {p}',
    'hud.strategy_hint': 'Estratégia: {label}',
    'hud.streak_sparkline_title': 'Sequência da sessão (atual: {current:+d})',
    'hud.training_badge': 'Treino: {correct}/{total} ({pct:.0f}%)',
    'insurance.no': 'Não',
    'insurance.yes': 'Seguro (Sim)',
    'leaderboard.back_button': 'Voltar',
    'leaderboard.col_achievements': 'Conquistas',
    'leaderboard.col_best_streak': 'Melhor sequência',
    'leaderboard.col_blackjacks': 'Blackjacks',
    'leaderboard.col_chips': 'Fichas',
    'leaderboard.col_hands': 'Mãos',
    'leaderboard.col_name': 'Perfil',
    'leaderboard.col_rank': '#',
    'leaderboard.col_win_pct': '% Vitórias',
    'leaderboard.empty_state': 'Ainda não há perfis para comparar.',
    'leaderboard.hint_esc_exit': 'Esc/Voltar para sair',
    'leaderboard.sort_hint': 'Clica numa coluna para ordenar por ela',
    'leaderboard.title': 'Classificação de perfis',
    'menu.back_button': 'Voltar',
    'menu.challenges_button': 'Desafios',
    'menu.custom_hint': 'Prime Enter ou JOGAR para ajustar as tuas próprias regras',
    'menu.custom_option': 'Personalizado...',
    'menu.dealer_hit_h17': 'Pede carta (H17)',
    'menu.dealer_stand_s17': 'Fica (S17)',
    'menu.double_9_10_11': 'Apenas 9, 10 ou 11',
    'menu.double_any_two': 'Quaisquer 2 cartas',
    'menu.field.blackjack_payout': 'Pagamento de Blackjack',
    'menu.field.dealer_rule': 'Crupiê em soft 17',
    'menu.field.double_after_split': 'Dobrar após split (DAS)',
    'menu.field.double_rule': 'Dobrar permitido com',
    'menu.field.even_money_allowed': 'Even Money',
    'menu.field.five_card_charlie': 'Five Card Charlie',
    'menu.field.hit_split_aces': 'Pedir carta após dividir Ases',
    'menu.field.insurance_allowed': 'Seguro permitido',
    'menu.field.max_bet': 'Aposta máxima',
    'menu.field.max_splits': 'Splits máximos',
    'menu.field.min_bet': 'Aposta mínima',
    'menu.field.num_decks': 'Baralhos',
    'menu.field.original_bets_only': 'OBBO (BJ do crupiê)',
    'menu.field.penetration': 'Penetração do sapato',
    'menu.field.perfect_pairs_allowed': 'Aposta lateral: Pares Perfeitos',
    'menu.field.resplit_aces': 'Voltar a dividir Ases',
    'menu.field.side_bet_max': 'Limite de aposta lateral',
    'menu.field.starting_chips': 'Fichas iniciais',
    'menu.field.surrender_rule': 'Render-se (Surrender)',
    'menu.field.twentyone_plus_three_allowed': 'Aposta lateral: 21+3',
    'menu.hint_base': 'Setas cima/baixo para selecionar · Enter para jogar',
    'menu.hint_history_suffix': ' · H: histórico',
    'menu.history_button': 'Histórico',
    'menu.max_splits_fmt': '{v} (até {n} mãos)',
    'menu.no': 'Não',
    'menu.play_button': 'JOGAR',
    'menu.player_label': 'Jogador: {name}',
    'menu.reset_button': 'Repor',
    'menu.rules_editor_title': 'REGRAS PERSONALIZADAS',
    'menu.rules_hint': 'Setas para mover e alterar valores · Enter/JOGAR confirma · Esc/Voltar cancela',
    'menu.select_casino': 'Seleciona o casino:',
    'menu.settings_button': 'Definições',
    'menu.surrender_early': 'Antecipado',
    'menu.surrender_late': 'Tardio',
    'menu.surrender_none': 'Não permitido',
    'menu.yes': 'Sim',
    'profile.add_player_button': '+  Adicionar jogador',
    'profile.avatar_label': 'Avatar:',
    'profile.cancel_button': 'Cancelar',
    'profile.chips_hands_info': '{chips:.0f} fichas · {hands} mãos jogadas',
    'profile.confirm_delete': 'Eliminar? Clica novamente para confirmar',
    'profile.create_button': 'Criar',
    'profile.create_hint': 'Setas para escolher avatar · Enter para criar · Esc para voltar',
    'profile.create_title': 'Novo perfil',
    'profile.error_empty_name': 'Escreve um nome para o perfil.',
    'profile.leaderboard_button': 'Classificação',
    'profile.list_hint': 'Clica num perfil para continuar · lista: ver histórico · lixo: eliminar · N: novo perfil · Classificação: comparar perfis',
    'profile.max_players_note': 'Máximo de 3 jogadores na mesa',
    'profile.name_label': 'Nome:',
    'profile.new_profile_button': '+  Novo perfil',
    'profile.play_button': 'Jogar',
    'profile.play_solo_button': 'Jogar sozinho',
    'profile.seat_number': 'Lugar {n}',
    'profile.seats_hint_add': ' · A para adicionar outro jogador',
    'profile.seats_hint_play': 'Enter para jogar',
    'profile.seats_title': 'Jogadores na mesa',
    'profile.subtitle_default': 'Perfis locais — sem palavra-passe, cada um com o seu próprio histórico',
    'profile.subtitle_seat': 'Escolhe quem se senta no próximo lugar',
    'profile.title_default': 'Quem joga?',
    'profile_store.duplicate_name': 'Já existe um perfil chamado «{name}».',
    'profile_store.empty_name': 'O nome não pode estar vazio.',
    'renderer.action_double': 'Dobrar',
    'renderer.action_hit': 'Pedir carta',
    'renderer.action_split': 'Dividir',
    'renderer.action_stand': 'Ficar',
    'renderer.action_surrender': 'Render-se',
    'renderer.betting_hint': 'Clica nas fichas para apostar · Enter para distribuir',
    'renderer.betting_turn': 'Turno de aposta: {name}',
    'renderer.blackjack_bang': 'Blackjack!',
    'renderer.challenge_lost_title': 'DESAFIO FALHADO',
    'renderer.challenge_preset_label': 'Desafio: {name}',
    'renderer.challenge_won_title': 'DESAFIO CONCLUÍDO!',
    'renderer.continue_hint': 'Clica ou Enter para continuar',
    'renderer.deal_button': 'DEAL',
    'renderer.dealer_blackjack': 'O crupiê tem Blackjack',
    'renderer.dealer_busts': 'O crupiê rebenta!',
    'renderer.dealer_hits': 'O crupiê pede carta...',
    'renderer.dealer_reveals': 'O crupiê revela a sua carta...',
    'renderer.dealer_shows_ace': 'O crupiê mostra um Ás — Seguro?',
    'renderer.dealer_stands': 'O crupiê fica em {value}',
    'renderer.dealing_to': 'A distribuir a {name}...',
    'renderer.double_and_bust': '{name} dobra e rebenta ({value})',
    'renderer.double_result': '{name} dobra: {value}',
    'renderer.esc_to_menu': 'ESC -> Menu principal',
    'renderer.even_money_or_insurance': 'Even Money ou Seguro?',
    'renderer.final_chips_net_stat': 'Fichas finais: {chips}   Líquido: {net:+.0f}',
    'renderer.game_over_title': 'GAME OVER',
    'renderer.hand_n_label': 'Mão {n}: ',
    'renderer.hands_played_stat': 'Mãos jogadas: {n}',
    'renderer.keybinds_hint': 'F1: Dicas  F2: Contador  F3: Stats  F4: Conquistas  F5: Treino  M: Música  ESC: Menu',
    'renderer.min_bet_warning': 'Aposta mínima: ${amount}',
    'renderer.n_hands': '{n} mãos',
    'renderer.natural_blackjack': 'Blackjack de {name}!',
    'renderer.net_roi_stat': 'Líquido: {net:+.0f}   ROI: {roi:+.1%}',
    'renderer.player_n_fallback': 'Jogador {n}',
    'renderer.rebet_button': 'Repetir ${amount}',
    'renderer.reshuffling': 'A baralhar',
    'renderer.result_blackjack': 'BLACKJACK!',
    'renderer.result_dealer_bust': 'CRUPIÊ REBENTOU',
    'renderer.result_loss': 'PERDESTE',
    'renderer.result_push': 'EMPATE',
    'renderer.result_surrender': 'RENDIÇÃO',
    'renderer.result_win': 'GANHASTE',
    'renderer.round_result_title': 'RESULTADO DA RONDA',
    'renderer.seat_blackjack': 'BLACKJACK!',
    'renderer.seat_doubles': 'DOBRA',
    'renderer.seat_split_aces': 'ASES',
    'renderer.shoe_info': 'Sapato: {remaining}/{total}',
    'renderer.sidebet_perfect_pairs': 'Pares Perfeitos',
    'renderer.split_aces_result': '{name} separa os Ases: {v1} e {v2}',
    'renderer.status_betting': 'a apostar',
    'renderer.status_bust': 'rebentada ({value})',
    'renderer.status_dealing': 'a distribuir',
    'renderer.status_hand_value': 'mão: {value}',
    'renderer.status_in_game': 'em jogo',
    'renderer.status_insurance': 'seguro',
    'renderer.status_playing': 'a jogar',
    'renderer.status_stood': 'parado ({value})',
    'renderer.status_waiting': 'à espera',
    'renderer.title_add_seat': 'Quem mais se vai sentar?',
    'renderer.total_label': 'Total: {sign}{amount}',
    'renderer.training_correct': 'Correto!',
    'renderer.training_mode_toggle': 'Modo treino {state}',
    'renderer.training_off': 'desativado',
    'renderer.training_on': 'ativado',
    'renderer.training_should_have': 'Estratégia básica: {label}',
    'renderer.wlp_stat': 'W / L / P:  {w} / {l} / {p}',
    'replay.back_button': 'Voltar',
    'replay.dealer_label_empty': 'CRUPIÊ',
    'replay.dealer_label_value': 'CRUPIÊ  {value}',
    'replay.exit_hint': 'Esc/Voltar para sair',
    'replay.info_bar': '{date}   ·   {preset}   ·   Aposta: ${bet:.0f}',
    'replay.no_data': 'Não há dados de repetição guardados para esta mão.',
    'replay.parse_error': 'Não foi possível interpretar a repetição desta mão.',
    'replay.player_label_empty': 'A TUA MÃO',
    'replay.player_label_value': 'A TUA MÃO  {value}{tags}',
    'replay.tag_doubled': 'dobrada',
    'replay.tag_surrendered': 'rendida',
    'settings.audio_section': 'Áudio',
    'settings.card_back_section': 'Verso das cartas',
    'settings.hint': 'Clica para aplicar de imediato · arrasta os cursores de volume · Esc/Voltar para sair',
    'settings.language_section': 'Idioma',
    'settings.music_label': 'Música',
    'settings.muted': 'Silenciado',
    'settings.sfx_label': 'Efeitos sonoros',
    'settings.table_section': 'Mesa',
    'sidebets.perfect_pairs_label': 'Pares Perfeitos',
    'sidebets.title': 'Apostas laterais (opcional)',
    'table.bet_label': 'Aposta: {bet}',
    'table.dealer_label': 'CRUPIÊ  {value}',
    'table.hand_label': 'A TUA MÃO  {value}',
}
_STRINGS_DE: dict[str, str] = {
    'animations.achievement_for_player': 'ERFOLG VON {name}',
    'animations.achievement_unlocked': 'ERFOLG FREIGESCHALTET',
    'challenge.progress_chips': '${chips} / ${target}',
    'challenge.progress_hand': 'Hand {hand} / {limit}',
    'challenge.progress_net': 'Netto: {net:+.0f}',
    'challenge.progress_streak': 'Serie {cur} / {target}',
    'challenge_select.back_button': 'Zurück',
    'challenge_select.detail_bet_range': 'Einsatz: ${min} - ${max}',
    'challenge_select.detail_fail_on_loss': 'Jede Niederlage, jedes Unentschieden oder Aufgeben beendet die Herausforderung',
    'challenge_select.detail_hand_limit': 'Handlimit: {limit}',
    'challenge_select.detail_require_profit': 'Ziel: mit mehr Chips enden, als du gestartet bist',
    'challenge_select.detail_starting_chips': 'Startchips: ${chips}',
    'challenge_select.detail_target_chips': 'Ziel: ${target} Chips erreichen',
    'challenge_select.detail_target_streak': 'Ziel: eine Serie von {streak} Siegen in Folge',
    'challenge_select.hint': 'Pfeiltasten zum Navigieren · Enter/Starten bestätigt · Esc/Zurück bricht ab',
    'challenge_select.item_facts': '{limit} Hände · ${chips} Startguthaben',
    'challenge_select.start_button': 'Herausforderung starten',
    'challenge_select.subtitle': 'Kurze Partien mit einem klaren Ziel -- ideal für eine schnelle Runde',
    'challenge_select.title': 'HERAUSFORDERUNGEN',
    'chipstack.undo_hint': 'Rechtsklick -> letzten Chip zurücknehmen',
    'counter.cold': 'Kalt ❄️',
    'counter.hot': 'Heiß 🔥',
    'counter.neutral': 'Neutral ➖',
    'counter.very_cold': 'Sehr kalt 🥶',
    'counter.very_hot': 'Sehr heiß! 🌋',
    'counter.warm': 'Warm 🌡️',
    'engine.action_unavailable': "Aktion '{action}' derzeit nicht verfügbar.",
    'engine.dealer_has_blackjack': 'Der Dealer hat Blackjack!',
    'engine.even_money_paid': '{name}: Even Money ausgezahlt.',
    'engine.invalid_bet': 'Ungültiger Einsatz. Min={min}, Max={max}',
    'engine.invalid_side_bet': 'Ungültige Nebenwette. Max={max}',
    'engine.not_enough_chips': 'Du hast nicht genug Chips.',
    'engine.out_of_chips': 'Du hast keine Chips mehr! Spiel beendet.',
    'engine.reshuffling': 'Der Schuh wird neu gemischt...',
    'history.back_button': 'Zurück',
    'history.chip_evolution_label': 'Chip-Verlauf (letzte {n} Hände)',
    'history.col_bet': 'Einsatz',
    'history.col_casino': 'Casino',
    'history.col_chips': 'Chips',
    'history.col_date': 'Datum',
    'history.col_net': 'Netto',
    'history.col_result': 'Ergebnis',
    'history.default_player_name': 'Spieler',
    'history.empty_state': 'Mit diesem Profil wurden noch keine Hände gespielt.',
    'history.hint_esc_exit': 'Esc/Zurück zum Verlassen',
    'history.hint_page_arrows': 'Pfeiltasten zum Seitenwechsel',
    'history.hint_tab_switch': 'Tab zum Profilwechsel',
    'history.pagination_label': 'Seite {page} / {total_pages}  ·  {total} Hände insgesamt',
    'history.result_blackjack_win': 'Blackjack!',
    'history.result_dealer_bust': 'Dealer überkauft',
    'history.result_loss': 'Verloren',
    'history.result_push': 'Unentschieden',
    'history.result_surrender': 'Aufgegeben',
    'history.result_win': 'Gewonnen',
    'history.title_for_profile': 'Verlauf von {name}',
    'hud.achievements_title': 'Erfolge  ({n}/{total})',
    'hud.action_double_or_hit': 'Double (sonst Hit)',
    'hud.action_double_or_stand': 'Double (sonst Stand)',
    'hud.action_split_or_hit': 'Split (sonst Hit)',
    'hud.action_surrender_or_hit': 'Surrender (sonst Hit)',
    'hud.action_surrender_or_split': 'Surrender (sonst Split)',
    'hud.action_surrender_or_stand': 'Surrender (sonst Stand)',
    'hud.category_blackjack': 'Blackjack',
    'hud.category_bust': 'Überkauft',
    'hud.category_count_label': '{label}: {n}',
    'hud.category_loss': 'Niederlage',
    'hud.category_push': 'Unentschieden',
    'hud.category_surrender': 'Aufgegeben',
    'hud.category_win': 'Sieg',
    'hud.challenge_hands_progress': 'Hand {played}/{limit}',
    'hud.result_distribution_title': 'Ergebnisverteilung',
    'hud.stat_best_streak': 'Beste Serie: +{n}',
    'hud.stat_blackjacks': 'Blackjacks: {n}',
    'hud.stat_busts': 'Überkäufe:  {n}',
    'hud.stat_chips': 'Chips:  {chips}',
    'hud.stat_hands': 'Hände:   {n}',
    'hud.stat_net': 'Netto:    {net:+.0f}',
    'hud.stat_player': 'Spieler: {name}',
    'hud.stat_roi': 'ROI:     {roi:+.1%}',
    'hud.stat_winrate': 'Gewinnrate: {pct:.1%}',
    'hud.stat_wlp': 'W / L / P: {w} / {l} / {p}',
    'hud.strategy_hint': 'Strategie: {label}',
    'hud.streak_sparkline_title': 'Serie der Sitzung (aktuell: {current:+d})',
    'hud.training_badge': 'Training: {correct}/{total} ({pct:.0f}%)',
    'insurance.no': 'Nein',
    'insurance.yes': 'Versicherung (Ja)',
    'leaderboard.back_button': 'Zurück',
    'leaderboard.col_achievements': 'Erfolge',
    'leaderboard.col_best_streak': 'Beste Serie',
    'leaderboard.col_blackjacks': 'Blackjacks',
    'leaderboard.col_chips': 'Chips',
    'leaderboard.col_hands': 'Hände',
    'leaderboard.col_name': 'Profil',
    'leaderboard.col_rank': '#',
    'leaderboard.col_win_pct': '% Siege',
    'leaderboard.empty_state': 'Es gibt noch keine Profile zum Vergleichen.',
    'leaderboard.hint_esc_exit': 'Esc/Zurück zum Verlassen',
    'leaderboard.sort_hint': 'Klick auf eine Spalte zum Sortieren',
    'leaderboard.title': 'Profil-Bestenliste',
    'menu.back_button': 'Zurück',
    'menu.challenges_button': 'Herausforderungen',
    'menu.custom_hint': 'Drücke Enter oder SPIELEN, um deine eigenen Regeln festzulegen',
    'menu.custom_option': 'Benutzerdefiniert...',
    'menu.dealer_hit_h17': 'Zieht (H17)',
    'menu.dealer_stand_s17': 'Bleibt stehen (S17)',
    'menu.double_9_10_11': 'Nur 9, 10 oder 11',
    'menu.double_any_two': 'Beliebige 2 Karten',
    'menu.field.blackjack_payout': 'Blackjack-Auszahlung',
    'menu.field.dealer_rule': 'Dealer bei Soft 17',
    'menu.field.double_after_split': 'Verdoppeln nach Split (DAS)',
    'menu.field.double_rule': 'Verdoppeln erlaubt bei',
    'menu.field.even_money_allowed': 'Even Money',
    'menu.field.five_card_charlie': 'Five Card Charlie',
    'menu.field.hit_split_aces': 'Karte ziehen nach Ass-Split',
    'menu.field.insurance_allowed': 'Versicherung erlaubt',
    'menu.field.max_bet': 'Höchsteinsatz',
    'menu.field.max_splits': 'Max. Splits',
    'menu.field.min_bet': 'Mindesteinsatz',
    'menu.field.num_decks': 'Decks',
    'menu.field.original_bets_only': 'OBBO (Dealer-BJ)',
    'menu.field.penetration': 'Schuh-Penetration',
    'menu.field.perfect_pairs_allowed': 'Nebenwette: Perfect Pairs',
    'menu.field.resplit_aces': 'Asse erneut splitten',
    'menu.field.side_bet_max': 'Limit für Nebenwetten',
    'menu.field.starting_chips': 'Startchips',
    'menu.field.surrender_rule': 'Aufgeben (Surrender)',
    'menu.field.twentyone_plus_three_allowed': 'Nebenwette: 21+3',
    'menu.hint_base': 'Pfeiltasten hoch/runter zur Auswahl · Enter zum Spielen',
    'menu.hint_history_suffix': ' · H: Verlauf',
    'menu.history_button': 'Verlauf',
    'menu.max_splits_fmt': '{v} (bis zu {n} Hände)',
    'menu.no': 'Nein',
    'menu.play_button': 'SPIELEN',
    'menu.player_label': 'Spieler: {name}',
    'menu.reset_button': 'Zurücksetzen',
    'menu.rules_editor_title': 'BENUTZERDEFINIERTE REGELN',
    'menu.rules_hint': 'Pfeiltasten zum Navigieren und Ändern der Werte · Enter/SPIELEN bestätigt · Esc/Zurück bricht ab',
    'menu.select_casino': 'Casino auswählen:',
    'menu.settings_button': 'Einstellungen',
    'menu.surrender_early': 'Früh',
    'menu.surrender_late': 'Spät',
    'menu.surrender_none': 'Nicht erlaubt',
    'menu.yes': 'Ja',
    'profile.add_player_button': '+  Spieler hinzufügen',
    'profile.avatar_label': 'Avatar:',
    'profile.cancel_button': 'Abbrechen',
    'profile.chips_hands_info': '{chips:.0f} Chips · {hands} gespielte Hände',
    'profile.confirm_delete': 'Löschen? Nochmal klicken zum Bestätigen',
    'profile.create_button': 'Erstellen',
    'profile.create_hint': 'Pfeiltasten zur Avatar-Auswahl · Enter zum Erstellen · Esc zum Zurückgehen',
    'profile.create_title': 'Neues Profil',
    'profile.error_empty_name': 'Gib einen Namen für das Profil ein.',
    'profile.leaderboard_button': 'Bestenliste',
    'profile.list_hint': 'Klick auf ein Profil, um fortzufahren · Listensymbol: Verlauf ansehen · Papierkorb: löschen · N: neues Profil · Bestenliste: Profile vergleichen',
    'profile.max_players_note': 'Maximal 3 Spieler am Tisch',
    'profile.name_label': 'Name:',
    'profile.new_profile_button': '+  Neues Profil',
    'profile.play_button': 'Spielen',
    'profile.play_solo_button': 'Allein spielen',
    'profile.seat_number': 'Platz {n}',
    'profile.seats_hint_add': ' · A, um einen weiteren Spieler hinzuzufügen',
    'profile.seats_hint_play': 'Enter zum Spielen',
    'profile.seats_title': 'Spieler am Tisch',
    'profile.subtitle_default': 'Lokale Profile — kein Passwort, jedes mit eigener Historie',
    'profile.subtitle_seat': 'Wähle, wer sich auf den nächsten Platz setzt',
    'profile.title_default': 'Wer spielt?',
    'profile_store.duplicate_name': 'Ein Profil namens „{name}“ existiert bereits.',
    'profile_store.empty_name': 'Der Name darf nicht leer sein.',
    'renderer.action_double': 'Verdoppeln',
    'renderer.action_hit': 'Karte ziehen',
    'renderer.action_split': 'Teilen',
    'renderer.action_stand': 'Stehen bleiben',
    'renderer.action_surrender': 'Aufgeben',
    'renderer.betting_hint': 'Klicke auf die Chips, um zu setzen · Enter zum Geben',
    'renderer.betting_turn': 'Einsatzrunde: {name}',
    'renderer.blackjack_bang': 'Blackjack!',
    'renderer.challenge_lost_title': 'HERAUSFORDERUNG GESCHEITERT',
    'renderer.challenge_preset_label': 'Herausforderung: {name}',
    'renderer.challenge_won_title': 'HERAUSFORDERUNG GESCHAFFT!',
    'renderer.continue_hint': 'Klick oder Enter zum Fortfahren',
    'renderer.deal_button': 'GEBEN',
    'renderer.dealer_blackjack': 'Der Dealer hat Blackjack',
    'renderer.dealer_busts': 'Der Dealer überkauft sich!',
    'renderer.dealer_hits': 'Der Dealer zieht eine Karte...',
    'renderer.dealer_reveals': 'Der Dealer deckt seine Karte auf...',
    'renderer.dealer_shows_ace': 'Der Dealer zeigt ein Ass — Versicherung?',
    'renderer.dealer_stands': 'Der Dealer bleibt bei {value} stehen',
    'renderer.dealing_to': 'Austeilen an {name}...',
    'renderer.double_and_bust': '{name} verdoppelt und überkauft sich ({value})',
    'renderer.double_result': '{name} verdoppelt: {value}',
    'renderer.esc_to_menu': 'ESC -> Hauptmenü',
    'renderer.even_money_or_insurance': 'Even Money oder Versicherung?',
    'renderer.final_chips_net_stat': 'Endchips: {chips}   Netto: {net:+.0f}',
    'renderer.game_over_title': 'GAME OVER',
    'renderer.hand_n_label': 'Hand {n}: ',
    'renderer.hands_played_stat': 'Gespielte Hände: {n}',
    'renderer.keybinds_hint': 'F1: Hinweise  F2: Zähler  F3: Statistik  F4: Erfolge  F5: Training  M: Musik  ESC: Menü',
    'renderer.min_bet_warning': 'Mindesteinsatz: ${amount}',
    'renderer.n_hands': '{n} Hände',
    'renderer.natural_blackjack': '{name} hat Blackjack!',
    'renderer.net_roi_stat': 'Netto: {net:+.0f}   ROI: {roi:+.1%}',
    'renderer.player_n_fallback': 'Spieler {n}',
    'renderer.rebet_button': 'Wiederholen ${amount}',
    'renderer.reshuffling': 'Neu mischen',
    'renderer.result_blackjack': 'BLACKJACK!',
    'renderer.result_dealer_bust': 'DEALER ÜBERKAUFT',
    'renderer.result_loss': 'VERLOREN',
    'renderer.result_push': 'UNENTSCHIEDEN',
    'renderer.result_surrender': 'AUFGEGEBEN',
    'renderer.result_win': 'GEWONNEN',
    'renderer.round_result_title': 'RUNDENERGEBNIS',
    'renderer.seat_blackjack': 'BLACKJACK!',
    'renderer.seat_doubles': 'VERDOPPELT',
    'renderer.seat_split_aces': 'ASSE',
    'renderer.shoe_info': 'Schuh: {remaining}/{total}',
    'renderer.sidebet_perfect_pairs': 'Perfect Pairs',
    'renderer.split_aces_result': '{name} teilt die Asse: {v1} und {v2}',
    'renderer.status_betting': 'setzt',
    'renderer.status_bust': 'überkauft ({value})',
    'renderer.status_dealing': 'gibt Karten',
    'renderer.status_hand_value': 'Hand: {value}',
    'renderer.status_in_game': 'im Spiel',
    'renderer.status_insurance': 'Versicherung',
    'renderer.status_playing': 'spielt',
    'renderer.status_stood': 'steht ({value})',
    'renderer.status_waiting': 'wartet',
    'renderer.title_add_seat': 'Wer setzt sich noch dazu?',
    'renderer.total_label': 'Gesamt: {sign}{amount}',
    'renderer.training_correct': 'Richtig!',
    'renderer.training_mode_toggle': 'Trainingsmodus {state}',
    'renderer.training_off': 'deaktiviert',
    'renderer.training_on': 'aktiviert',
    'renderer.training_should_have': 'Grundstrategie: {label}',
    'renderer.wlp_stat': 'W / L / P:  {w} / {l} / {p}',
    'replay.back_button': 'Zurück',
    'replay.dealer_label_empty': 'DEALER',
    'replay.dealer_label_value': 'DEALER  {value}',
    'replay.exit_hint': 'Esc/Zurück zum Verlassen',
    'replay.info_bar': '{date}   ·   {preset}   ·   Einsatz: ${bet:.0f}',
    'replay.no_data': 'Für diese Hand sind keine Wiederholungsdaten gespeichert.',
    'replay.parse_error': 'Die Wiederholung dieser Hand konnte nicht gelesen werden.',
    'replay.player_label_empty': 'DEINE HAND',
    'replay.player_label_value': 'DEINE HAND  {value}{tags}',
    'replay.tag_doubled': 'verdoppelt',
    'replay.tag_surrendered': 'aufgegeben',
    'settings.audio_section': 'Audio',
    'settings.card_back_section': 'Kartenrückseite',
    'settings.hint': 'Klick zum sofortigen Anwenden · zieh die Lautstärkeregler · Esc/Zurück zum Verlassen',
    'settings.language_section': 'Sprache',
    'settings.music_label': 'Musik',
    'settings.muted': 'Stummgeschaltet',
    'settings.sfx_label': 'Soundeffekte',
    'settings.table_section': 'Tisch',
    'sidebets.perfect_pairs_label': 'Perfect Pairs',
    'sidebets.title': 'Nebenwetten (optional)',
    'table.bet_label': 'Einsatz: {bet}',
    'table.dealer_label': 'DEALER  {value}',
    'table.hand_label': 'DEINE HAND  {value}',
}
STRINGS["fr"].update(_STRINGS_FR)
STRINGS["pt"].update(_STRINGS_PT)
STRINGS["de"].update(_STRINGS_DE)
