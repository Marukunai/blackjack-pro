# ui/card_sprite.py
# CardSprite: carta animada con deslizamiento suave y flip 3D al revelar.
# -------------------------------------------------------------
from __future__ import annotations

import pygame
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ui.card_generator import CardGenerator
    from core.card import Card

from config import settings as cfg


class CardSprite:
    """
    Envuelve una Surface de carta con posición, animación de
    deslizamiento (deal) y flip horizontal (reveal hole card).
    """

    DEAL_SPEED   = 18     # px/frame durante el deslizamiento
    FLIP_SPEED   = 0.12   # fracción de escala por frame

    def __init__(
        self,
        card: "Card",
        generator: "CardGenerator",
        target_x: int,
        target_y: int,
        start_x: Optional[int] = None,
        start_y: Optional[int] = None,
        delay: int = 0,          # frames de espera antes de arrancar
    ) -> None:
        self.card      = card
        self.generator = generator
        self.target_x  = target_x
        self.target_y  = target_y
        self.x         = float(start_x if start_x is not None else target_x)
        self.y         = float(start_y if start_y is not None else target_y)
        self.delay     = delay

        # Estado de animación
        self._dealing  = (start_x is not None or start_y is not None)
        self._flipping = False
        self._flip_scale = 1.0       # 1 → 0 → 1 (flip horizontal)
        self._flip_phase = 0         # 0=reduciendo, 1=ampliando

        # Superficie actual
        self._update_surface()

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    def update(self) -> None:
        if self.delay > 0:
            self.delay -= 1
            return

        # Animación de deslizamiento
        if self._dealing:
            dx = self.target_x - self.x
            dy = self.target_y - self.y
            dist = (dx**2 + dy**2) ** 0.5
            if dist < self.DEAL_SPEED:
                self.x = float(self.target_x)
                self.y = float(self.target_y)
                self._dealing = False
            else:
                factor = self.DEAL_SPEED / dist
                self.x += dx * factor
                self.y += dy * factor

        # Animación de flip
        if self._flipping:
            if self._flip_phase == 0:
                self._flip_scale -= self.FLIP_SPEED
                if self._flip_scale <= 0.0:
                    self._flip_scale = 0.0
                    self._flip_phase = 1
                    self._update_surface()   # cambia la cara en el punto medio
            else:
                self._flip_scale += self.FLIP_SPEED
                if self._flip_scale >= 1.0:
                    self._flip_scale = 1.0
                    self._flipping = False

    def draw(self, surface: pygame.Surface) -> None:
        if self.delay > 0:
            return

        src = self._surface
        if self._flipping and self._flip_scale < 1.0:
            new_w = max(1, int(src.get_width() * self._flip_scale))
            scaled = pygame.transform.scale(src, (new_w, src.get_height()))
            ox = int(self.x) + (src.get_width() - new_w) // 2
            surface.blit(scaled, (ox, int(self.y)))
        else:
            surface.blit(src, (int(self.x), int(self.y)))

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

    def move_to(self, x: int, y: int) -> None:
        self.target_x = x
        self.target_y = y
        self._dealing = True

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