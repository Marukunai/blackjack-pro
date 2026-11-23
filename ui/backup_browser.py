# ui/backup_browser.py
# Fase 32: pantalla para elegir un archivo de copia de seguridad de
# perfil (ver engine/profile_backup.py) e importarlo como un perfil
# nuevo. Como el juego no tiene (ni necesita) un selector de archivos
# nativo, se limita a listar los .json de saves/backups/ -- el mismo
# sitio donde el botón "Exportar" de ui/profile_select.py los deja --
# ordenados por fecha, más reciente primero.
# -------------------------------------------------------------
from __future__ import annotations

import time
import pygame
from pathlib import Path
from typing import Optional

from config import settings as cfg
from config import i18n
from ui import icons
from engine.profile_backup import (
    preview_profile_backup, import_profile_backup, BackupError, BACKUPS_DIR,
)


class _FileRow:
    def __init__(self, path: Path, preview: dict, rect: pygame.Rect) -> None:
        self.path = path
        self.preview = preview
        self.rect = rect
        self.hover = False


class BackupBrowseScreen:
    """Bucle bloqueante. Devuelve (profile_id, nombre) del perfil recién
    importado, o None si se cancela (ESC/Volver) o no hay nada que
    importar."""

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.sw, self.sh = screen.get_size()
        self._done = False
        self._result: Optional[tuple[int, str]] = None
        self._error_msg = ""

        self._font_title = pygame.font.SysFont(None, 36, bold=True)
        self._font_body  = pygame.font.SysFont(None, 20)
        self._font_small = pygame.font.SysFont(None, 16)

        self._back_rect = pygame.Rect(self.sw // 2 - 90, self.sh - 70, 180, 44)
        self._back_hover = False

        self._rows: list[_FileRow] = []
        self._build_rows()

    # ------------------------------------------------------------------
    def _build_rows(self) -> None:
        self._rows.clear()
        if not BACKUPS_DIR.exists():
            return
        files = sorted(BACKUPS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        row_w, row_h, gap = 560, 56, 10
        top = 140
        x = self.sw // 2 - row_w // 2
        for i, path in enumerate(files):
            try:
                preview = preview_profile_backup(path)
            except BackupError:
                continue
            rect = pygame.Rect(x, top + i * (row_h + gap), row_w, row_h)
            self._rows.append(_FileRow(path, preview, rect))

    # ------------------------------------------------------------------
    def run(self) -> Optional[tuple[int, str]]:
        clock = pygame.time.Clock()
        while not self._done:
            clock.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit
                self._handle_event(event)
            self._draw()
            pygame.display.flip()
        return self._result

    def _handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._done = True
        if event.type == pygame.MOUSEMOTION:
            self._back_hover = self._back_rect.collidepoint(event.pos)
            for row in self._rows:
                row.hover = row.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._back_rect.collidepoint(event.pos):
                self._done = True
                return
            for row in self._rows:
                if row.rect.collidepoint(event.pos):
                    self._import_row(row)
                    return

    def _import_row(self, row: "_FileRow") -> None:
        """Importa el archivo elegido como un perfil nuevo. Si el nombre
        ya está en uso, se añade un sufijo automáticamente (sin pedirle
        al jugador que escriba un nombre alternativo -- esta pantalla no
        tiene campo de texto) probando hasta encontrar uno libre."""
        base_name = row.preview["name"]
        candidate = base_name
        suffix = 1
        while True:
            try:
                pid = import_profile_backup(row.path, new_name=candidate)
                self._result = (pid, candidate)
                self._done = True
                return
            except BackupError as exc:
                suffix += 1
                if suffix > 25:
                    self._error_msg = str(exc)
                    return
                candidate = i18n.t("backup.import_name_suffix", name=base_name, n=suffix)

    # ------------------------------------------------------------------
    def _draw(self) -> None:
        surf = self.screen
        surf.fill(cfg.COLOR_BG)

        title = self._font_title.render(i18n.t("backup.browse_title"), True, cfg.COLOR_GOLD)
        surf.blit(title, (self.sw // 2 - title.get_width() // 2, 60))

        if not self._rows:
            empty = self._font_body.render(i18n.t("backup.browse_empty"), True, (150, 150, 150))
            surf.blit(empty, (self.sw // 2 - empty.get_width() // 2, self.sh // 2 - 10))
        else:
            for row in self._rows:
                self._draw_row(surf, row)

        if self._error_msg:
            err = self._font_small.render(self._error_msg, True, cfg.COLOR_LOSE)
            surf.blit(err, (self.sw // 2 - err.get_width() // 2, self.sh - 118))

        back_col = cfg.COLOR_GOLD if self._back_hover else (150, 150, 150)
        pygame.draw.rect(surf, (20, 15, 0), self._back_rect, border_radius=10)
        pygame.draw.rect(surf, back_col, self._back_rect, 2, border_radius=10)
        back_txt = self._font_body.render(i18n.t("backup.back_button"), True, back_col)
        surf.blit(back_txt, (self._back_rect.centerx - back_txt.get_width() // 2,
                              self._back_rect.centery - back_txt.get_height() // 2))

    def _draw_row(self, surf: pygame.Surface, row: "_FileRow") -> None:
        r = row.rect
        bg = (255, 255, 255, 26) if row.hover else (255, 255, 255, 10)
        box = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
        pygame.draw.rect(box, bg, box.get_rect(), border_radius=10)
        pygame.draw.rect(box, cfg.COLOR_GOLD if row.hover else (90, 90, 90),
                          box.get_rect(), 1, border_radius=10)
        surf.blit(box, (r.x, r.y))

        icons.upload_icon(surf, r.x + 30, r.centery, 13, cfg.COLOR_GOLD if row.hover else (160, 160, 160))

        p = row.preview
        name = self._font_body.render(p["name"], True, cfg.COLOR_TEXT)
        surf.blit(name, (r.x + 56, r.y + 8))

        exported_at = p.get("exported_at")
        date_str = time.strftime("%d/%m/%Y %H:%M", time.localtime(exported_at)) if exported_at else "—"
        info = self._font_small.render(
            i18n.t("backup.browse_item_info", date=date_str, chips=int(p["chips"]),
                   hands=p["hand_count"], achievements=p["achievement_count"]),
            True, (150, 150, 150),
        )
        surf.blit(info, (r.x + 56, r.y + 30))
