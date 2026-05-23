# 🃏 Blackjack Pro

Juego de Blackjack profesional con gráficos 2D en Python + Pygame.

## Características
- Soporte para 1, 2, 4, 6 y 8 mazos
- Todas las acciones: Hit, Stand, Double Down, Split, Surrender, Insurance, Even Money
- Presets de casino: Vegas Strip, Atlantic City, European, Single Deck
- Sistema de hints con estrategia básica completa
- Contador de cartas Hi-Lo visual
- Animaciones de cartas, fichas y efectos de partículas
- Estadísticas de sesión detalladas

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate      # macOS/Linux
# .venv\Scripts\activate       # Windows

pip install -r requirements.txt
python main.py
```

## Estructura del proyecto

```
blackjack_pro/
├── core/       # Lógica pura: cartas, mazos, manos, jugadores, reglas
├── engine/     # Motor de partida: estados, acciones, pagos, estadísticas
├── ai/         # Estrategia básica y contador Hi-Lo
├── ui/         # Gráficos Pygame: mesa, sprites, HUD, animaciones, menú
├── assets/     # Cartas, fichas, fuentes, sonidos, texturas
├── config/     # Configuración y presets de reglas
├── saves/      # Perfil del jugador (fichas, récords)
└── tests/      # Tests unitarios e integración
```

## Tests

```bash
python -m pytest tests/ -v
```
