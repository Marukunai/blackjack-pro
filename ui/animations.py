# ui/animations.py
# Efectos de partículas: win glow, bust humo, blackjack destello dorado.
# -------------------------------------------------------------
from __future__ import annotations

import math
import random
import pygame
from typing import Optional


class Particle:
    def __init__(self, x: float, y: float, color: tuple,
                 vx: float, vy: float, size: float, life: int):
        self.x, self.y = x, y
        self.color = color
        self.vx, self.vy = vx, vy
        self.size = size
        self.life = life
        self.max_life = life

    def update(self) -> bool:
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.08   # gravedad suave
        self.life -= 1
        return self.life > 0

    def draw(self, surf: pygame.Surface) -> None:
        alpha = int(255 * (self.life / self.max_life))
        r = max(1, int(self.size * (self.life / self.max_life)))
        col = (*self.color[:3], alpha)
        s = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
        pygame.draw.circle(s, col, (r, r), r)
        surf.blit(s, (int(self.x) - r, int(self.y) - r))


class ParticleSystem:
    def __init__(self):
        self.particles: list[Particle] = []

    def emit_win(self, cx: int, cy: int) -> None:
        """Lluvia de monedas doradas."""
        for _ in range(40):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(1.5, 5.0)
            self.particles.append(Particle(
                cx, cy,
                color=random.choice([(255, 215, 0), (255, 180, 0), (220, 200, 60)]),
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed - 2,
                size=random.uniform(3, 7),
                life=random.randint(40, 80),
            ))

    def emit_blackjack(self, cx: int, cy: int) -> None:
        """Explosión dorada espectacular."""
        for _ in range(80):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(2.0, 8.0)
            self.particles.append(Particle(
                cx, cy,
                color=random.choice([(255, 215, 0), (255, 255, 100), (255, 140, 0), (200, 255, 100)]),
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed - 3,
                size=random.uniform(4, 10),
                life=random.randint(60, 120),
            ))

    def emit_bust(self, cx: int, cy: int) -> None:
        """Humo rojo de derrota."""
        for _ in range(30):
            self.particles.append(Particle(
                cx + random.randint(-20, 20),
                cy + random.randint(-10, 10),
                color=random.choice([(200, 40, 40), (180, 60, 60), (150, 30, 30)]),
                vx=random.uniform(-1.5, 1.5),
                vy=random.uniform(-3.0, -0.5),
                size=random.uniform(4, 9),
                life=random.randint(30, 60),
            ))

    def update(self) -> None:
        self.particles = [p for p in self.particles if p.update()]

    def draw(self, surf: pygame.Surface) -> None:
        for p in self.particles:
            p.draw(surf)

    def clear(self) -> None:
        self.particles.clear()


class GlowEffect:
    """Halo pulsante alrededor de una zona (Blackjack, mano activa…)."""

    def __init__(self, color: tuple, radius: int = 18, speed: float = 0.06):
        self.color  = color
        self.radius = radius
        self.speed  = speed
        self._phase = 0.0

    def update(self) -> None:
        self._phase = (self._phase + self.speed) % (2 * math.pi)

    def draw(self, surf: pygame.Surface, rect: pygame.Rect) -> None:
        alpha = int(80 + 60 * math.sin(self._phase))
        r = int(self.radius + 4 * math.sin(self._phase * 1.5))
        glow_surf = pygame.Surface(
            (rect.width + r*2, rect.height + r*2), pygame.SRCALPHA
        )
        pygame.draw.rect(
            glow_surf,
            (*self.color[:3], alpha),
            pygame.Rect(0, 0, rect.width + r*2, rect.height + r*2),
            border_radius=r + 8,
        )
        surf.blit(glow_surf, (rect.x - r, rect.y - r))


class ResultBanner:
    """Banner de resultado que aparece y desaparece con fade."""

    DURATION = 90   # frames

    def __init__(self, text: str, color: tuple):
        self.text   = text
        self.color  = color
        self._timer = self.DURATION
        self._font  = None

    def _ensure_font(self) -> None:
        if self._font is None:
            self._font = pygame.font.SysFont(None, 52, bold=True)

    def update(self) -> bool:
        self._timer -= 1
        return self._timer > 0

    def draw(self, surf: pygame.Surface, cx: int, cy: int) -> None:
        self._ensure_font()
        alpha = min(255, int(255 * min(1.0, self._timer / 20)))
        # Subir ligeramente a medida que desaparece
        offset_y = int((self.DURATION - self._timer) * 0.4)

        shadow = self._font.render(self.text, True, (0, 0, 0))
        text_s = self._font.render(self.text, True, self.color)

        # Aplicar alpha
        shadow.set_alpha(alpha // 2)
        text_s.set_alpha(alpha)

        x = cx - text_s.get_width() // 2
        y = cy - text_s.get_height() // 2 - offset_y

        surf.blit(shadow, (x+2, y+2))
        surf.blit(text_s, (x, y))