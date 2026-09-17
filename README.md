# 🃏 Blackjack Pro

Juego de Blackjack profesional con gráficos 2D en Python + Pygame. Todos los
gráficos, animaciones y sonidos son procedurales (generados por código, sin
archivos de imagen ni audio), así que el proyecto entero cabe en unos pocos
megabytes de código puro.

## Características

**Reglas y mesa**
- Presets de casino: Vegas Strip, Atlantic City, European, Single Deck, y un
  editor de reglas personalizadas (17 parámetros: número de mazos,
  penetración, pagos de Blackjack, doblar tras split, resplit, seguro,
  rendición, etc.)
- Soporte para 1, 2, 4, 6 y 8 mazos
- Todas las acciones: Hit, Stand, Double Down, Split (con resplit), Surrender,
  Insurance / Even Money
- Apuestas laterales opcionales: Perfect Pairs y 21+3
- Multijugador local por turnos ("hot-seat"), de 1 a 3 jugadores en la misma
  mesa

**Ayudas y estadísticas**
- Modo entrenamiento (F5): compara cada jugada contra la estrategia básica en
  vivo, con marcador de acierto
- Contador de cartas Hi-Lo visual (F2)
- Sugerencias de estrategia básica (F1) y panel de estadísticas de sesión (F3)
- Perfiles de jugador locales (sin contraseña) con historial de manos
  persistente, comparativa/leaderboard entre perfiles, gráfica de evolución
  de fichas y repetición visual de cualquier mano jugada
- 21 logros desbloqueables (F4)

**Presentación**
- Animaciones de cartas, fichas y efectos de partículas; audio ambiente y
  efectos de sonido, todo generado por código (M silencia/activa la música)
- Temas visuales intercambiables: color del fieltro de la mesa y reverso de
  las cartas, más control de volumen, todo desde "Ajustes" y persistente
  entre partidas

## Instalación

### Opción 1 — Instalador de Windows (recomendado para jugar)

Descarga o genera `BlackjackPro_Setup.exe` (ver "Generar el instalador" más
abajo) y ejecútalo. No hace falta tener Python instalado ni permisos de
administrador. Crea acceso directo en el menú inicio (y, si lo marcas, en el
escritorio) junto con su propio desinstalador. Las partidas guardadas viven
en su propia carpeta `saves`, separada del programa, así que desinstalar
nunca las borra.

### Opción 2 — Desde el código fuente (para jugar en otros sistemas o para desarrollo)

```bash
python -m venv .venv
source .venv/bin/activate      # macOS/Linux
# .venv\Scripts\activate       # Windows

pip install -r requirements.txt
python main.py                 # interfaz gráfica (Pygame)
python main.py console         # modo consola interactivo
```

## Generar el .exe / el instalador (solo Windows)

```
build_exe.bat         → genera dist\BlackjackPro.exe (PyInstaller, un solo archivo)
build_installer.bat   → genera dist_installer\BlackjackPro_Setup.exe (requiere Inno Setup,
                         gratis en https://jrsoftware.org/isdl.php — el script lo detecta solo)
```

`build_installer.bat` genera primero el `.exe` si no existe, así que basta con
correr ese script directamente.

## Estructura del proyecto

```
blackjack_pro/
├── core/       # Lógica pura: cartas, mazos, manos, jugadores, reglas
├── engine/     # Motor de partida: estados, acciones, pagos, estadísticas,
│               # perfiles/SQLite, historial de manos, logros, ajustes
├── ai/         # Estrategia básica y contador de cartas Hi-Lo
├── ui/         # Gráficos Pygame: mesa, sprites, HUD, animaciones, menú,
│               # perfiles, historial, comparativa, ajustes, repetición de mano
├── config/     # Configuración, presets de reglas y temas visuales
├── assets/     # Solo icon.ico (el icono de la app) -- el resto de gráficos
│               # y sonidos son procedurales, no hay imágenes ni audio en disco
├── saves/      # Base de datos SQLite con perfiles, fichas e historial
│               # (se crea sola al arrancar; nunca se toca al instalar/desinstalar)
├── tests/      # Tests unitarios de la lógica base (mazos, manos, pagos, motor)
├── main.py             # Punto de entrada (gráfico o consola)
├── build_exe.bat       # Genera el .exe con PyInstaller
├── build_installer.bat # Genera el instalador con Inno Setup
└── installer.iss       # Script de Inno Setup
```

## Tests

```bash
python -m pytest tests/ -v
```

Estos tests cubren la lógica base (mazos, manos, pagos, motor de partida). El
resto de funcionalidades (UI, multijugador, perfiles, logros, apuestas
laterales, modo entrenamiento, repetición de mano, instalador...) se ha ido
verificando con baterías de pruebas propias en cada fase de desarrollo antes
de cada entrega.

## Controles rápidos

| Tecla | Acción |
|---|---|
| F1 | Mostrar/ocultar sugerencia de estrategia básica |
| F2 | Mostrar/ocultar contador de cartas Hi-Lo |
| F3 | Panel de estadísticas de sesión |
| F4 | Panel de logros |
| F5 | Modo entrenamiento (compara tus jugadas con la estrategia básica) |
| H | Historial de manos (desde el menú principal) |
| M | Silenciar/activar la música |
| Esc | Volver al menú |
