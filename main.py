"""
main.py — Punto de entrada de Blackjack Pro
Uso:
    python main.py          → UI gráfica Pygame (por defecto)
    python main.py console  → modo consola interactivo
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "pygame"

    if mode == "console":
        from play_console import main
        main()
    else:
        try:
            import pygame
        except ImportError:
            print("Pygame no está instalado. Ejecuta: pip install pygame")
            print("O usa el modo consola: python main.py console")
            sys.exit(1)

        from ui.renderer import launch
        launch()