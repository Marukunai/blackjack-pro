# ui/icons.py
# Iconos vectoriales dibujados con primitivas de Pygame (círculos,
# polígonos, arcos). No dependen de que el sistema tenga instalada una
# fuente con soporte de símbolos/emoji — que es justo lo que causaba los
# recuadros "tofu" [] cuando el glifo (♠ ★ ► ↺ 💰 🃏 …) no existía en la
# fuente por defecto. Un palo de carta dibujado a mano también es, de
# hecho, más fiel a como se ven las cartas reales que un glifo Unicode.
# -------------------------------------------------------------
from __future__ import annotations

import math
import pygame

RED_SUITS   = ("H", "D")
BLACK_SUITS = ("S", "C")


def suit_color(suit_letter: str, red: tuple, black: tuple) -> tuple:
    return red if suit_letter in RED_SUITS else black


def draw_suit(surf: pygame.Surface, suit_letter: str, cx: float, cy: float,
              size: float, color: tuple) -> None:
    """Dibuja el símbolo del palo (S/H/D/C) centrado en (cx, cy).
    `size` es la altura aproximada total del símbolo en px."""
    cx, cy = float(cx), float(cy)

    if suit_letter == "D":
        h, w = size * 0.52, size * 0.36
        pygame.draw.polygon(surf, color, [
            (cx, cy - h), (cx + w, cy), (cx, cy + h), (cx - w, cy),
        ])

    elif suit_letter == "H":
        r = size * 0.28
        pygame.draw.circle(surf, color, (cx - r * 0.95, cy - r * 0.35), r)
        pygame.draw.circle(surf, color, (cx + r * 0.95, cy - r * 0.35), r)
        pygame.draw.polygon(surf, color, [
            (cx - r * 1.9, cy - r * 0.15),
            (cx + r * 1.9, cy - r * 0.15),
            (cx, cy + r * 1.9),
        ])

    elif suit_letter == "S":
        r = size * 0.28
        pygame.draw.circle(surf, color, (cx - r * 0.95, cy + r * 0.45), r)
        pygame.draw.circle(surf, color, (cx + r * 0.95, cy + r * 0.45), r)
        pygame.draw.polygon(surf, color, [
            (cx - r * 1.9, cy + r * 0.65),
            (cx + r * 1.9, cy + r * 0.65),
            (cx, cy - r * 2.0),
        ])
        stem_w = size * 0.11
        pygame.draw.polygon(surf, color, [
            (cx - stem_w, cy + r * 1.3), (cx + stem_w, cy + r * 1.3),
            (cx + stem_w * 1.9, cy + size * 0.5), (cx - stem_w * 1.9, cy + size * 0.5),
        ])

    elif suit_letter == "C":
        r = size * 0.22
        pygame.draw.circle(surf, color, (cx, cy - r * 1.15), r)
        pygame.draw.circle(surf, color, (cx - r * 1.0, cy + r * 0.35), r)
        pygame.draw.circle(surf, color, (cx + r * 1.0, cy + r * 0.35), r)
        stem_w = size * 0.10
        pygame.draw.polygon(surf, color, [
            (cx - stem_w, cy + r * 0.3), (cx + stem_w, cy + r * 0.3),
            (cx + stem_w * 1.9, cy + size * 0.55), (cx - stem_w * 1.9, cy + size * 0.55),
        ])


def triangle_right(surf: pygame.Surface, x: float, y: float, size: float, color: tuple) -> None:
    """Triángulo apuntando a la derecha (play/deal). (x, y) = borde izquierdo, centrado en altura."""
    h = size
    pygame.draw.polygon(surf, color, [
        (x, y - h / 2), (x, y + h / 2), (x + h * 0.9, y),
    ])


def triangle_left(surf: pygame.Surface, x: float, y: float, size: float, color: tuple) -> None:
    """Triángulo apuntando a la izquierda (selector de valor anterior).
    (x, y) = borde derecho, centrado en altura -- espejo de triangle_right."""
    h = size
    pygame.draw.polygon(surf, color, [
        (x, y - h / 2), (x, y + h / 2), (x - h * 0.9, y),
    ])


def check_mark(surf: pygame.Surface, cx: float, cy: float, size: float, color: tuple, width: int = 3) -> None:
    """Marca de verificación (✓) centrada en (cx, cy)."""
    s = size
    pts = [
        (cx - s * 0.5, cy),
        (cx - s * 0.12, cy + s * 0.42),
        (cx + s * 0.55, cy - s * 0.42),
    ]
    pygame.draw.lines(surf, color, False, pts, width)


def cross_mark(surf: pygame.Surface, cx: float, cy: float, size: float, color: tuple, width: int = 3) -> None:
    """Aspa (✗) centrada en (cx, cy)."""
    s = size * 0.5
    pygame.draw.line(surf, color, (cx - s, cy - s), (cx + s, cy + s), width)
    pygame.draw.line(surf, color, (cx - s, cy + s), (cx + s, cy - s), width)


def star(surf: pygame.Surface, cx: float, cy: float, r_outer: float, color: tuple,
         points: int = 5, r_inner_ratio: float = 0.42, rotation: float = -math.pi / 2) -> None:
    """Estrella de N puntas rellena, centrada en (cx, cy)."""
    pts = []
    for i in range(points * 2):
        r = r_outer if i % 2 == 0 else r_outer * r_inner_ratio
        ang = rotation + i * math.pi / points
        pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    pygame.draw.polygon(surf, color, pts)


def refresh_arrow(surf: pygame.Surface, cx: float, cy: float, r: float, color: tuple, width: int = 2) -> None:
    """Flecha circular (repetir apuesta / deshacer), arco ~280° con punta de flecha."""
    rect = pygame.Rect(cx - r, cy - r, r * 2, r * 2)
    start_ang = math.radians(15)
    end_ang = math.radians(305)
    pygame.draw.arc(surf, color, rect, start_ang, end_ang, width)

    tip_x = cx + r * math.cos(start_ang)
    tip_y = cy - r * math.sin(start_ang)
    tang = start_ang + math.pi / 2
    pygame.draw.polygon(surf, color, [
        (tip_x + 6 * math.cos(start_ang), tip_y - 6 * math.sin(start_ang)),
        (tip_x + 5 * math.cos(tang), tip_y - 5 * math.sin(tang)),
        (tip_x - 5 * math.cos(tang), tip_y + 5 * math.sin(tang)),
    ])


def coin(surf: pygame.Surface, cx: float, cy: float, r: float,
         bg_color: tuple, text_color: tuple, font: pygame.font.Font) -> None:
    """Ficha/moneda con '$' dentro (sustituye al emoji de dinero)."""
    pygame.draw.circle(surf, bg_color, (cx, cy), r)
    ring = tuple(min(255, c + 55) for c in bg_color[:3])
    pygame.draw.circle(surf, ring, (cx, cy), r, 2)
    t = font.render("$", True, text_color)
    surf.blit(t, (cx - t.get_width() // 2, cy - t.get_height() // 2))


def hline(surf: pygame.Surface, x: float, y: float, w: float, color: tuple, thickness: int = 1) -> None:
    """Línea horizontal decorativa (sustituye divisores de texto hechos con '─')."""
    pygame.draw.line(surf, color, (x, y), (x + w, y), thickness)


def list_icon(surf: pygame.Surface, cx: float, cy: float, size: float, color: tuple,
              width: int = 2) -> None:
    """Icono de lista/historial: tres líneas horizontales, cada una con un
    punto a la izquierda (como un renglón de una tabla). Centrado en
    (cx, cy); `size` controla la altura aproximada total del icono."""
    cx, cy = float(cx), float(cy)
    line_w = size * 1.3
    gap = size * 0.55
    dot_r = max(1.5, size * 0.09)
    for dy in (-gap, 0.0, gap):
        y = cy + dy
        pygame.draw.circle(surf, color, (cx - line_w / 2 - dot_r * 2.5, y), dot_r)
        pygame.draw.line(surf, color, (cx - line_w / 2, y), (cx + line_w / 2, y), width)


def gear_icon(surf: pygame.Surface, cx: float, cy: float, size: float, color: tuple,
              teeth: int = 8) -> None:
    """Icono de engranaje (ajustes/preferencias): núcleo circular con
    dientes radiales cortos, centrado en (cx, cy). A tamaños pequeños
    (los que usa este juego para botones de menú) se lee con más
    claridad como una rueda sólida con púas que como un anillo hueco con
    un agujero central, así que se dibuja relleno en vez de con hueco."""
    cx, cy = float(cx), float(cy)
    r = size
    pygame.draw.circle(surf, color, (cx, cy), r * 0.62)
    tooth_len = r * 0.4
    tooth_w = max(2, r * 0.34)
    for i in range(teeth):
        ang = 2 * math.pi * i / teeth
        x1 = cx + math.cos(ang) * r * 0.55
        y1 = cy + math.sin(ang) * r * 0.55
        x2 = cx + math.cos(ang) * (r * 0.55 + tooth_len)
        y2 = cy + math.sin(ang) * (r * 0.55 + tooth_len)
        pygame.draw.line(surf, color, (x1, y1), (x2, y2), int(tooth_w))


def bars_icon(surf: pygame.Surface, cx: float, cy: float, size: float, color: tuple) -> None:
    """Icono de barras ascendentes (comparativa/leaderboard/estadísticas):
    tres barras de alturas crecientes, apoyadas en una línea base común,
    centrado en (cx, cy)."""
    cx, cy = float(cx), float(cy)
    bar_w = size * 0.34
    gap = size * 0.14
    heights = (size * 0.55, size * 0.85, size * 1.15)
    total_w = bar_w * 3 + gap * 2
    x = cx - total_w / 2
    base_y = cy + size * 0.6
    for h in heights:
        rect = pygame.Rect(int(x), int(base_y - h), max(1, int(bar_w)), int(h))
        pygame.draw.rect(surf, color, rect, border_radius=1)
        x += bar_w + gap
