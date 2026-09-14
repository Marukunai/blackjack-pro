# ui/card_sprite.py
# CardSprite: carta animada con deslizamiento suave (ease-out), ligero
# arco de vuelo, rotación al repartir, sombra dinámica y flip 3D al revelar.
# -------------------------------------------------------------
from __future__ import annotations

import math
import random
import pygame
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ui.card_generator import CardGenerator
    from core.card import Card

from config import settings as cfg


class CardSprite:
    """
    Envuelve una Surface de carta con posición, animación de
    deslizamiento (deal) con ease-out + arco + rotación, sombra
    dinámica de contacto, y flip horizontal (reveal hole card).
    """

    DEAL_EASE    = 0.24   # fracción de la distancia restante recorrida por frame
    SNAP_DIST    = 2.0    # px por debajo de los cuales se considera "llegada"
    FLIP_SPEED   = 0.14   # fracción de escala por frame
    MAX_TILT_DEG = 9.0    # inclinación máxima al salir disparada
    MAX_LIFT_PX  = 9.0    # "altura" máxima del arco a mitad de vuelo

    def __init__(
        self,
        card: "Card",
        generator: "CardGenerator",
        target_x: int,
        target_y: int,
        start_x: Optional[int] = None,
        start_y: Optional[int] = None,
        delay: int = 0,          # frames de espera antes de arrancar
        fan_rotation: float = 0.0,  # inclinación permanente (efecto abanico)
    ) -> None:
        self.card      = card
        self.generator = generator
        self.target_x  = target_x
        self.target_y  = target_y
        self.x         = float(start_x if start_x is not None else target_x)
        self.y         = float(start_y if start_y is not None else target_y)
        self.delay     = delay
        # Inclinación fija (no decae, a diferencia del tilt de vuelo): da el
        # efecto de abanico cuando una mano tiene varias cartas.
        self.fan_rotation = float(fan_rotation)

        # Estado de animación
        self._dealing  = (start_x is not None or start_y is not None)
        self._flipping = False
        self._flip_scale = 1.0       # 1 → 0 → 1 (flip horizontal)
        self._flip_phase = 0         # 0=reduciendo, 1=ampliando

        # Vuelo: distancia total del tramo actual, tilt inicial e "altura" visual
        self._flight_len   = 0.0
        self._motion_scale = 0.0   # atenúa tilt/arco en reposicionamientos cortos
        self._tilt0        = 0.0
        self._rotation     = 0.0
        self._lift          = 0.0
        if self._dealing:
            self._start_flight()

        # Caché de la superficie rotada: pygame.transform.rotate() crea una
        # Surface nueva cada vez y es caro — con el abanico la inclinación
        # queda fija en reposo, así que solo hay que recalcularla cuando el
        # ángulo (o la cara de la carta) realmente cambian, no cada frame.
        self._rot_cache_angle: Optional[float] = None
        self._rot_cache_src = None
        self._rot_cache_surf: Optional[pygame.Surface] = None

        # Superficie actual
        self._update_surface()

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    def _start_flight(self) -> None:
        self._flight_len = math.hypot(self.target_x - self.x, self.target_y - self.y)
        # Vuelos cortos (reposicionar cartas ya en mesa) apenas se inclinan/levantan
        self._motion_scale = min(1.0, self._flight_len / 150.0)
        self._tilt0 = random.uniform(-self.MAX_TILT_DEG, self.MAX_TILT_DEG) * self._motion_scale

    def update(self) -> None:
        if self.delay > 0:
            self.delay -= 1
            return

        speed = max(0.1, getattr(cfg, "ANIMATION_SPEED", 1.0))

        # Animación de deslizamiento (ease-out con arco y rotación)
        if self._dealing:
            dx = self.target_x - self.x
            dy = self.target_y - self.y
            dist = math.hypot(dx, dy)

            if dist < self.SNAP_DIST or self._flight_len < 1e-3:
                self.x = float(self.target_x)
                self.y = float(self.target_y)
                self._dealing  = False
                self._rotation = 0.0
                self._lift     = 0.0
            else:
                factor = min(1.0, self.DEAL_EASE * speed)
                self.x += dx * factor
                self.y += dy * factor

                frac_remaining = min(1.0, dist / self._flight_len)
                self._rotation = self._tilt0 * frac_remaining
                self._lift = (self.MAX_LIFT_PX * self._motion_scale *
                              math.sin(math.pi * (1.0 - frac_remaining)))

        # Animación de flip
        if self._flipping:
            step = self.FLIP_SPEED * speed
            if self._flip_phase == 0:
                self._flip_scale -= step
                if self._flip_scale <= 0.0:
                    self._flip_scale = 0.0
                    self._flip_phase = 1
                    self._update_surface()   # cambia la cara en el punto medio
            else:
                self._flip_scale += step
                if self._flip_scale >= 1.0:
                    self._flip_scale = 1.0
                    self._flipping = False

    def draw(self, surface: pygame.Surface) -> None:
        if self.delay > 0:
            return

        # Sombra de contacto dinámica: más difusa y separada cuanto más "alta" vuela
        if self._dealing:
            self._draw_shadow(surface)

        src = self._surface
        if self._flipping and self._flip_scale < 1.0:
            new_w = max(1, int(src.get_width() * self._flip_scale))
            scaled = pygame.transform.scale(src, (new_w, src.get_height()))
            ox = int(self.x) + (src.get_width() - new_w) // 2
            surface.blit(scaled, (ox, int(self.y - self._lift)))
            return

        total_rotation = self._rotation + self.fan_rotation
        if abs(total_rotation) > 0.3:
            if (self._rot_cache_surf is None or
                    self._rot_cache_angle != total_rotation or
                    self._rot_cache_src is not src):
                self._rot_cache_surf = pygame.transform.rotate(src, -total_rotation)
                self._rot_cache_angle = total_rotation
                self._rot_cache_src = src
            rotated = self._rot_cache_surf
            cx = self.x + src.get_width() / 2
            cy = self.y - self._lift + src.get_height() / 2
            rect = rotated.get_rect(center=(cx, cy))
            surface.blit(rotated, rect)
        else:
            surface.blit(src, (int(self.x), int(self.y - self._lift)))

    def _draw_shadow(self, surface: pygame.Surface) -> None:
        w, h = cfg.CARD_WIDTH, cfg.CARD_HEIGHT
        lift_frac = min(1.0, self._lift / max(1.0, self.MAX_LIFT_PX))
        shadow_w = max(4, int(w * (0.88 - 0.10 * lift_frac)))
        shadow_h = max(3, int(h * 0.16))
        alpha = max(18, int(65 - 35 * lift_frac))

        shadow = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, alpha), shadow.get_rect())

        cx = int(self.x + w / 2 - shadow_w / 2)
        cy = int(self.y + h - shadow_h / 2 + 2 + lift_frac * 5)
        surface.blit(shadow, (cx, cy))

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------
    def flip_reveal(self) -> None:
        """Inicia la animación de flip para revelar la carta."""
        if not self._flipping and not self.card.face_up:
            self.card.reveal()
            self._flipping = True
            self._flip_scale = 1.0
            self._flip_phase = 0

    def move_to(self, x: int, y: int, fan_rotation: Optional[float] = None) -> None:
        self.target_x = x
        self.target_y = y
        if fan_rotation is not None:
            self.fan_rotation = float(fan_rotation)
        self._dealing = True
        self._start_flight()

    def set_fan_rotation(self, deg: float) -> None:
        """Actualiza la inclinación de abanico sin disparar una animación
        de vuelo (para cartas que no cambian de posición pero sí de
        inclinación al añadirse/quitarse cartas en la misma mano)."""
        self.fan_rotation = float(deg)

    @property
    def is_animating(self) -> bool:
        return self._dealing or self._flipping or self.delay > 0

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), cfg.CARD_WIDTH, cfg.CARD_HEIGHT)

    # ------------------------------------------------------------------
    # Interno
    # ------------------------------------------------------------------
    def _update_surface(self) -> None:
        if self.card.face_up:
            self._surface = self.generator.get(self.card.asset_name)
        else:
            self._surface = self.generator.get_back()
