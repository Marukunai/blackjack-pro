# ui/chip_stack.py
# Fichas de casino clicables para apostar.
# Click izquierdo  → añade ficha a la apuesta
# Click derecho    → devuelve la última ficha apostada (deshacer)
# -------------------------------------------------------------
from __future__ import annotations

import math
import pygame
from typing import Callable, Optional
from config import settings as cfg
from config import i18n

CHIP_DEFS = [
    (5,    (230, 230, 230), (60,  60,  60)),
    (10,   (220, 50,  50),  (255, 255, 255)),
    (25,   (40,  155, 70),  (255, 255, 255)),
    (50,   (50,  50,  210), (255, 255, 255)),
    (100,  (50,  15,  15),  (255, 215, 0)),
    (500,  (75,  15,  110), (255, 215, 0)),
]

CHIP_R   = 28
CHIP_GAP = 12


class Chip:
    def __init__(self, value: int, bg: tuple, text_col: tuple,
                 x: int, y: int, callback: Callable) -> None:
        self.value    = value
        self.bg       = bg
        self.text_col = text_col
        self.center   = (x, y)
        self.callback = callback
        self._hover   = False
        self._font: Optional[pygame.font.Font] = None

    def _ensure_font(self) -> None:
        if self._font is None:
            self._font = pygame.font.SysFont(None, 17, bold=True)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            dx = event.pos[0] - self.center[0]
            dy = event.pos[1] - self.center[1]
            self._hover = (dx*dx + dy*dy) <= CHIP_R * CHIP_R
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            dx = event.pos[0] - self.center[0]
            dy = event.pos[1] - self.center[1]
            if (dx*dx + dy*dy) <= CHIP_R * CHIP_R:
                self.callback(self.value)
                return True
        return False

    def draw(self, surf: pygame.Surface, enabled: bool = True) -> None:
        self._ensure_font()
        r = CHIP_R + (2 if self._hover and enabled else 0)
        cx, cy = self.center
        col = self.bg if enabled else (60, 60, 60)

        # Sombra
        shadow_s = pygame.Surface((r*2+6, r*2+6), pygame.SRCALPHA)
        pygame.draw.circle(shadow_s, (0, 0, 0, 50), (r+3, r+4), r)
        surf.blit(shadow_s, (cx - r - 3, cy - r - 3))

        pygame.draw.circle(surf, col, (cx, cy), r)
        ring = tuple(min(255, c + 60) for c in col) if enabled else (90, 90, 90)
        pygame.draw.circle(surf, ring, (cx, cy), r, 2)
        pygame.draw.circle(surf, ring, (cx, cy), int(r * 0.74), 1)

        for angle_deg in range(0, 360, 45):
            rad = math.radians(angle_deg)
            nx = int(cx + (r - 5) * math.cos(rad))
            ny = int(cy + (r - 5) * math.sin(rad))
            pygame.draw.circle(surf, ring, (nx, ny), 3)

        label = f"${self.value}" if self.value < 1000 else f"${self.value//1000}K"
        tc = self.text_col if enabled else (130, 130, 130)
        t = self._font.render(label, True, tc)
        surf.blit(t, (cx - t.get_width()//2, cy - t.get_height()//2))

        if self._hover and enabled:
            glow = pygame.Surface((r*2+10, r*2+10), pygame.SRCALPHA)
            pygame.draw.circle(glow, (255, 255, 255, 50), (r+5, r+5), r+4)
            surf.blit(glow, (cx - r - 5, cy - r - 5))


CHIP_SPAWN_FRAMES = 10   # frames del "pop" de aparición de cada ficha apostada
CHIP_FLIGHT_FRAMES = 24  # frames del vuelo de fichas al resolver la ronda


class BetStack:
    """Pila visual de fichas apostadas en la mesa, apiladas con offset 3D."""
    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y
        # Historial de fichas apostadas: dicts {value, bg, tc, age}
        self._chips: list[dict] = []
        # Fichas "en vuelo" tras resolverse la ronda (ver resolve())
        self._flying: list[dict] = []

    def push(self, value: int) -> None:
        bg, tc = (200, 200, 200), (60, 60, 60)
        for v, b, t in CHIP_DEFS:
            if v == value:
                bg, tc = b, t
                break
        self._chips.append({"value": value, "bg": bg, "tc": tc, "age": 0})

    def pop(self) -> Optional[int]:
        if self._chips:
            c = self._chips.pop()
            return c["value"]
        return None

    def clear(self) -> None:
        self._chips.clear()
        self._flying.clear()

    def resolve(self, target: Optional[tuple[int, int]]) -> None:
        """Convierte las fichas apostadas en fichas 'voladoras': si `target`
        se indica (ganancia → contador de fichas / pérdida → zona del
        crupier) vuelan hacia ahí; si es None (empate), simplemente se
        desvanecen en su sitio. Usado al resolver el pago de la ronda."""
        for i, c in enumerate(self._chips):
            offset_y = -i * 5
            x0, y0 = float(self.x), float(self.y + offset_y)
            tx, ty = target if target is not None else (x0, y0)
            self._flying.append({
                "value": c["value"], "bg": c["bg"], "tc": c["tc"],
                "x0": x0, "y0": y0, "tx": float(tx), "ty": float(ty),
                "age": 0, "delay": i * 2,
            })
        self._chips.clear()

    def update(self) -> None:
        """Avanza la animación de aparición ('pop') de cada ficha apostada
        y el vuelo/desvanecido de las fichas ya resueltas."""
        for c in self._chips:
            if c["age"] < CHIP_SPAWN_FRAMES:
                c["age"] += 1

        still = []
        for f in self._flying:
            if f["delay"] > 0:
                f["delay"] -= 1
                still.append(f)
                continue
            f["age"] += 1
            if f["age"] < CHIP_FLIGHT_FRAMES + 2:
                still.append(f)
        self._flying = still

    @property
    def total(self) -> int:
        return sum(c["value"] for c in self._chips)

    @property
    def count(self) -> int:
        return len(self._chips)

    def draw(self, surf: pygame.Surface) -> None:
        if self._chips:
            self._draw_bet_chips(surf)
        if self._flying:
            self._draw_flying_chips(surf)

    def _draw_bet_chips(self, surf: pygame.Surface) -> None:
        font = pygame.font.SysFont(None, 15, bold=True)
        base_r = 20
        for i, c in enumerate(self._chips):
            value, bg, tc = c["value"], c["bg"], c["tc"]
            # Ease-out cúbico: la ficha "cae" y crece hasta su tamaño final
            t = min(1.0, c["age"] / CHIP_SPAWN_FRAMES)
            ease = 1 - (1 - t) ** 3
            scale = 0.45 + 0.55 * ease
            drop  = int((1 - ease) * 16)
            r = max(4, int(base_r * scale))

            offset_y = -i * 5
            cx, cy = self.x, self.y + offset_y - drop
            ring = tuple(min(255, ch + 50) for ch in bg)
            # Sombra
            sh = pygame.Surface((r*2+4, r*2+4), pygame.SRCALPHA)
            pygame.draw.circle(sh, (0, 0, 0, 40), (r+2, r+3), r)
            surf.blit(sh, (cx - r - 2, cy - r - 2))
            pygame.draw.circle(surf, bg, (cx, cy), r)
            pygame.draw.circle(surf, ring, (cx, cy), r, 2)
            if scale > 0.7:
                label = f"${value}" if value < 1000 else f"${value//1000}K"
                t_surf = font.render(label, True, tc)
                surf.blit(t_surf, (cx - t_surf.get_width()//2, cy - t_surf.get_height()//2))

        # Total encima
        tf = pygame.font.SysFont(None, 18, bold=True)
        top_y = self.y - len(self._chips) * 5 - base_r - 8
        ts = tf.render(f"${self.total}", True, cfg.COLOR_GOLD)
        surf.blit(ts, (self.x - ts.get_width()//2, top_y))

    def _draw_flying_chips(self, surf: pygame.Surface) -> None:
        font = pygame.font.SysFont(None, 15, bold=True)
        base_r = 20
        fade_start = 0.6   # a partir de este % de progreso, la ficha se desvanece/encoge
        for f in self._flying:
            if f["delay"] > 0:
                continue
            t = min(1.0, f["age"] / CHIP_FLIGHT_FRAMES)
            ease = t * t * (3 - 2 * t)   # smoothstep: acelera y frena con suavidad
            x = f["x0"] + (f["tx"] - f["x0"]) * ease
            arc = math.sin(math.pi * t) * 16
            y = f["y0"] + (f["ty"] - f["y0"]) * ease - arc

            if t < fade_start:
                alpha, scale = 255, 1.0
            else:
                k = (t - fade_start) / (1 - fade_start)
                alpha = int(255 * max(0.0, 1 - k))
                scale = max(0.25, 1 - 0.75 * k)

            r = max(2, int(base_r * scale))
            bg, tc, value = f["bg"], f["tc"], f["value"]
            ring = tuple(min(255, ch + 50) for ch in bg)

            chip_s = pygame.Surface((r*2+4, r*2+4), pygame.SRCALPHA)
            pygame.draw.circle(chip_s, (*bg, alpha), (r+2, r+2), r)
            pygame.draw.circle(chip_s, (*ring, alpha), (r+2, r+2), r, 2)
            if scale > 0.6:
                label = f"${value}" if value < 1000 else f"${value//1000}K"
                t_surf = font.render(label, True, tc)
                t_surf.set_alpha(alpha)
                chip_s.blit(t_surf, (r+2 - t_surf.get_width()//2, r+2 - t_surf.get_height()//2))
            surf.blit(chip_s, (int(x) - r - 2, int(y) - r - 2))


class ChipTray:
    """
    Bandeja de fichas.
    Click izquierdo  → añade ficha.
    Click derecho    → devuelve la última ficha.
    """
    def __init__(self, screen_w: int, screen_h: int, callback: Callable) -> None:
        self._add_cb    = callback
        self._remove_cb: Optional[Callable] = None
        self._chips: list[Chip] = []
        self._enabled = True
        self._sw = screen_w
        self._sh = screen_h
        self._bet_stack = BetStack(screen_w // 2, int(screen_h * 0.42))
        self._font: Optional[pygame.font.Font] = None
        self._build(screen_w, screen_h)

    def set_remove_callback(self, fn: Callable) -> None:
        """fn() se llama al hacer click derecho para deshacer la última ficha."""
        self._remove_cb = fn

    def _build(self, sw: int, sh: int) -> None:
        n = len(CHIP_DEFS)
        total_w = n * (CHIP_R*2) + (n-1) * CHIP_GAP
        start_x = sw // 2 - total_w // 2 + CHIP_R
        y = sh - CHIP_R - 75
        for i, (value, bg, tc) in enumerate(CHIP_DEFS):
            x = start_x + i * (CHIP_R*2 + CHIP_GAP)
            self._chips.append(Chip(value, bg, tc, x, y, self._add_cb))

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def push_chip(self, value: int) -> None:
        """Registra visualmente la ficha apostada en la pila."""
        self._bet_stack.push(value)

    def pop_chip(self) -> Optional[int]:
        """Retira visualmente la última ficha de la pila."""
        return self._bet_stack.pop()

    def clear_stack(self) -> None:
        self._bet_stack.clear()

    def fly_result(self, target: Optional[tuple[int, int]]) -> None:
        """Lanza la animación de resolución de la apuesta: `target` es el
        punto hacia el que vuelan las fichas (ganancia/pérdida) o None para
        que se desvanezcan en su sitio (empate)."""
        self._bet_stack.resolve(target)

    def update(self) -> None:
        self._bet_stack.update()

    def draw_bet(self, surf: pygame.Surface) -> None:
        """Dibuja solo la pila de fichas apostadas (sin la bandeja de clic),
        para mantenerla visible en la mesa durante toda la mano."""
        self._bet_stack.draw(surf)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self._enabled:
            return False
        # Click derecho en cualquier lugar → deshacer última ficha
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            if self._remove_cb:
                self._remove_cb()
            return True
        for chip in self._chips:
            if chip.handle_event(event):
                return True
        return False

    def draw(self, surf: pygame.Surface, current_bet: int = 0,
             min_bet: int = 5, max_bet: int = 1000, chips: int = 1000) -> None:
        if self._font is None:
            self._font = pygame.font.SysFont(None, 20, bold=True)

        # Pila visual de fichas en la zona de apuesta
        self._bet_stack.draw(surf)

        for chip in self._chips:
            can_add = (self._enabled and
                       current_bet + chip.value <= max_bet and
                       chip.value <= chips)
            chip.draw(surf, enabled=can_add)

        # Hint click derecho
        if current_bet > 0 and self._enabled:
            hint_font = pygame.font.SysFont(None, 16)
            hint = hint_font.render(i18n.t("chipstack.undo_hint"), True, (90, 90, 90))
            y = self._chips[0].center[1] - CHIP_R - 22
            surf.blit(hint, (self._sw//2 - hint.get_width()//2, y))