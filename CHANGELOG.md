# Registro de cambios

Todas las versiones notables de Blackjack Pro se documentan en este archivo.

El formato sigue más o menos [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/),
y el versionado sigue [SemVer](https://semver.org/lang/es/). Las fases (Fase 1,
Fase 2...) hacen referencia a los hitos de desarrollo tal y como se han ido
nombrando en los mensajes de commit.

## [1.6.0] - 2026-10-19

### Añadido
- Fase 37: 4 logros nuevos (hasta 25 en total), ligados a apuestas
  laterales, a jugar contra un Bot y a hacer una copia de seguridad del
  perfil.
- Fase 38: personalidades de Bot al sentarlos en una mesa multijugador --
  Perfecto (estrategia básica pura, como hasta ahora), Conservador (nunca
  dobla ni separa) y Agresivo (dobla y separa más de la cuenta),
  elegibles por asiento.
- Fase 39: modo Torneo (`engine/tournament.py`, `ui/tournament_select.py`)
  -- 3 partidas a mesa completa (humanos + bots) con las mismas fichas
  para todos los asientos y un número fijo de manos; al terminar, una
  pantalla de clasificación final por fichas (oro/plata/bronce) decide
  quién gana. Reutiliza la configuración de asientos multijugador ya
  existente, igual que el modo Desafío reutiliza `Rules`.
- Fase 40: pulido de portfolio -- `LICENSE` (MIT), capturas de pantalla
  reales en `assets/screenshots/` y un `README.md` reorganizado con las
  características agrupadas por tema (reglas y mesa; oponentes IA y
  modos de juego; ayudas y estadísticas; idiomas, accesibilidad y
  presentación).
- Fase 41: accesibilidad básica desde "Ajustes" -- tamaño de letra grande
  y modo de alto contraste (`config/settings.py::apply_font_scale` /
  `apply_high_contrast`), aplicados al instante y persistentes entre
  partidas (`engine/app_settings.py`). El alto contraste afecta a toda la
  interfaz automáticamente; el tamaño de letra se ha aplicado a las
  pantallas que más se miran mientras se juega (mesa, HUD, botones de
  acción, fichas, apuestas laterales, menú principal).
- 14 tests nuevos (`tests/test_tournament.py`, `tests/test_accessibility.py`)
  cubriendo el modo Torneo y la accesibilidad básica (215 tests en total).

### Corregido
- `tests/test_engine.py::test_chips_decrease_on_bet` asumía que las
  fichas siempre bajan justo después de apostar, pero con un único
  jugador y `auto_advance=True` (modo consola) un Blackjack natural puede
  resolver la ronda entera -- reparto y pago 3:2 incluidos -- dentro de
  la propia llamada a `place_bet()`, dejando el saldo por encima del
  inicial. El test ahora distingue si la ronda se resolvió sola antes de
  comprobar el descuento exacto.

## [1.5.0] - 2026-10-16

### Añadido
- Fase 31: dos apuestas laterales nuevas, Lucky Ladies y Royal Match, junto
  a las ya existentes (Parejas Perfectas, 21+3) -- configurables por
  reglas, con su propio panel y pago.
- Fase 32: este mismo registro de cambios (`CHANGELOG.md`).
- Fase 33: suite de tests automatizados ampliada con `pytest` (de 50 a 152
  tests), cubriendo apuestas laterales, logros, desafíos, i18n, exportación
  CSV y el contador Hi-Lo -- hasta ahora sin cobertura permanente.
- Fase 34: copia de seguridad de perfil en JSON (exportar/importar) desde
  la pantalla de selección de perfil, para mover el progreso entre
  equipos sin depender de la base de datos SQLite local.
- Fase 35: oponentes controlados por IA ("Bot") que pueden sentarse en
  mesas multijugador junto a perfiles humanos, jugando con la misma
  estrategia básica que ya alimentaba las sugerencias en pantalla
  (`ai/basic_strategy.py`) -- pausados para que se note que "piensan",
  igual que el crupier.
- Fase 36: pantalla de tutorial / "Cómo jugar", accesible desde el menú
  principal, con páginas navegables sobre el objetivo del juego, el flujo
  de una ronda, las acciones disponibles y las apuestas laterales.

### Corregido
- `ai/basic_strategy.py` podía recomendar "rendirse" para una mano que ya
  no tenía esa opción disponible (p. ej. tras pedir carta, con más de 2
  cartas) -- al ejecutar esa recomendación a ciegas, un asiento de IA
  (Fase 35) podía quedarse congelado para siempre esperando una acción
  que el motor nunca iba a aceptar. Ahora la rendición solo se recomienda
  cuando sigue siendo una opción legal, y `ui/renderer.py` además
  comprueba que la acción recomendada sea realmente válida antes de
  ejecutarla, como red de seguridad adicional.

## [1.4.0] - 2026-09-17

### Añadido
- Fase 28: dos temas de mesa nuevos (esmeralda de lujo, púrpura real) y dos
  reversos de carta nuevos (púrpura real, negro y plata).
- Fase 29: exportación del historial de manos y las estadísticas del perfil
  a un archivo CSV, desde la pantalla de historial.
- Fase 30: modo de práctica de conteo de cartas (sistema Hi-Lo), con marca
  personal guardada por perfil.

### Corregido
- El banner de resultado de la pantalla "Repetir mano" mostraba la clave de
  traducción en crudo (p. ej. `history.result_win`) en lugar del texto
  traducido, desde que se introdujo el sistema de idiomas en la Fase 26.

## [1.3.0] - 2026-09-17

### Añadido
- Fase 27: soporte de francés, portugués y alemán (5 idiomas en total, junto
  a español e inglés).

## [1.2.0] - 2026-09-17

### Añadido
- Fases 23-26: más presets de reglas de casino, panel de estadísticas, modo
  Desafío, y soporte de inglés.

### Corregido
- Los Desafíos ahora siempre empiezan con sus propias fichas iniciales
  fijas, en vez de con el saldo real del perfil.
- Pausa indebida al splitear Ases en una partida multijugador.
- `build_installer.bat` no siempre recompilaba el `.exe` antes de empaquetar.

### Interno
- Higiene del repositorio: `.gitattributes` con finales de línea LF, y
  `profile.json.migrated` deja de versionarse.

## [1.0.0] - 2026-09-15

Primera versión jugable completa, antes de llevar un número de versión
explícito en el código (reconstruido aquí a partir del historial de commits).

### Añadido
- Lógica completa de una partida de Blackjack (mazo, reparto, acciones,
  pagos) sin interfaz gráfica.
- Interfaz gráfica con pygame: generación de cartas, mesa, botones de
  acción, HUD y partidas de Jugador contra el Crupier.
- Apuestas laterales en la interfaz (Parejas Perfectas, 21+3), sintetizador
  de efectos de sonido y música, y mejoras visuales en la mesa.

[1.6.0]: https://github.com/Marukunai/blackjack-pro/releases/tag/v1.6.0
[1.4.0]: https://github.com/Marukunai/blackjack-pro/releases/tag/v1.4.0
[1.3.0]: https://github.com/Marukunai/blackjack-pro/releases/tag/v1.3.0
[1.2.0]: https://github.com/Marukunai/blackjack-pro/releases/tag/v1.2.0
