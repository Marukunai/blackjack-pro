"""
main.py — Punto de entrada de Blackjack Pro
Ejecutar: python main.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

if __name__ == "__main__":
    from play_console import main
    main()