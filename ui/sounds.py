# ui/sounds.py
# SoundManager: sintetiza y reproduce los efectos de sonido del juego
# (reparto, flip, fichas, botones, victoria, blackjack, bust, empate,
# barajado) y una pista de ambiente de fondo en bucle, todo generado por
# código — sin depender de archivos de audio externos.
# -------------------------------------------------------------
from __future__ import annotations

import array
import math
import random
from typing import Optional

import pygame

from config import settings as cfg

SAMPLE_RATE = 44100


# ------------------------------------------------------------------
# Generación procedural de ondas (listas de muestras float en [-1, 1])
# ------------------------------------------------------------------
def _envelope(i: int, n: int, attack: float = 0.004, release: float = 0.05) -> float:
    a = min(1.0, i / max(1, SAMPLE_RATE * attack))
    r = min(1.0, (n - i) / max(1, SAMPLE_RATE * release))
    return a * r


def _tone_wave(freq_start: float, freq_end: float, duration: float,
               vol: float = 0.5, wave: str = "sine", noise: float = 0.0,
               release: float = 0.05) -> list[float]:
    """Tono con barrido de frecuencia (chirp) + envolvente de ataque/caída."""
    n = max(1, int(SAMPLE_RATE * duration))
    samples = [0.0] * n
    for i in range(n):
        t = i / SAMPLE_RATE
        frac = i / max(1, n - 1)
        freq = freq_start + (freq_end - freq_start) * frac
        phase = 2 * math.pi * freq * t
        s = (1.0 if math.sin(phase) >= 0 else -1.0) if wave == "square" else math.sin(phase)
        if noise:
            s = s * (1 - noise) + random.uniform(-1, 1) * noise
        samples[i] = s * _envelope(i, n, release=release) * vol
    return samples


def _sequence(freqs_hz: list[float], note_dur: float = 0.09,
              vol: float = 0.5, wave: str = "sine") -> list[float]:
    """Varias notas en secuencia (arpegio ascendente típico de victoria)."""
    out: list[float] = []
    for f in freqs_hz:
        out.extend(_tone_wave(f, f, note_dur, vol=vol, wave=wave, release=note_dur * 0.6))
    return out


def _noise_burst(duration: float, vol: float = 0.4) -> list[float]:
    """Ráfaga de ruido blanco con envolvente — cartas, barajado."""
    n = max(1, int(SAMPLE_RATE * duration))
    samples = [0.0] * n
    for i in range(n):
        env = _envelope(i, n, attack=0.002, release=duration * 0.7)
        samples[i] = random.uniform(-1, 1) * env * vol
    return samples


def _mix(*layers: list[float]) -> list[float]:
    n = max(len(l) for l in layers)
    out = [0.0] * n
    for layer in layers:
        for i, s in enumerate(layer):
            out[i] += s
    peak = max(1e-6, max(abs(s) for s in out))
    if peak > 1.0:
        out = [s / peak for s in out]
    return out


def _fade_edges(samples: list[float], fade_s: float = 0.35) -> list[float]:
    """Aplica un fundido corto de entrada/salida a los extremos del buffer.
    Se usa en la pista de ambiente para que el punto de bucle (donde
    pygame vuelve a empezar el buffer con loops=-1) no suene como un
    "clic" — un empalme perfecto de fase sería más trabajo del que
    merece una música de fondo discreta; un fundido breve es inaudible
    y evita el chasquido."""
    n = len(samples)
    nf = max(1, min(n // 2, int(SAMPLE_RATE * fade_s)))
    out = list(samples)
    for i in range(nf):
        a = i / nf
        out[i] *= a
        out[n - 1 - i] *= a
    return out


def _ambient_track(duration: float = 24.0, vol: float = 0.5) -> list[float]:
    """Pista de ambiente en bucle: un pad armónico suave con cambios de
    acorde lentos (progresión lounge/jazz discreta: Am7 - Dm7 - Gmaj7 -
    Cmaj7) más un leve "shimmer" de armónico alto con vibrato lento,
    pensada como música de fondo de casino que no compita con los SFX."""
    chords = [
        [220.00, 261.63, 329.63, 392.00],   # A3 C4 E4 G4  (Am7)
        [293.66, 349.23, 440.00, 523.25],   # D4 F4 A4 C5  (Dm7)
        [196.00, 246.94, 293.66, 369.99],   # G3 B3 D4 F#4 (Gmaj7)
        [261.63, 329.63, 392.00, 493.88],   # C4 E4 G4 B4  (Cmaj7)
    ]
    n_total = int(SAMPLE_RATE * duration)
    seg = n_total // len(chords)
    samples = [0.0] * n_total
    xfade_s = 0.9   # fundido entre acordes consecutivos, para que el cambio no "salte"

    for ci, chord in enumerate(chords):
        start = ci * seg
        end = n_total if ci == len(chords) - 1 else start + seg
        seg_len = end - start
        nfx = min(seg_len // 2, int(SAMPLE_RATE * xfade_s))
        for i in range(seg_len):
            t = (start + i) / SAMPLE_RATE
            local_fade = min(1.0, i / max(1, nfx), (seg_len - i) / max(1, nfx))
            s = 0.0
            for h, f in enumerate(chord):
                s += math.sin(2 * math.pi * f * t) * (0.85 ** h)
            # Shimmer: un armónico agudo muy tenue con vibrato lento, para
            # dar algo de "brillo" sin que resulte una melodía reconocible.
            shimmer_f = chord[-1] * 2
            shimmer = math.sin(2 * math.pi * shimmer_f * t + 0.6 * math.sin(2 * math.pi * 0.15 * t))
            s += shimmer * 0.10
            samples[start + i] = s * local_fade * vol / (len(chord) * 0.8)

    samples = _fade_edges(samples, fade_s=0.4)
    peak = max(1e-6, max(abs(x) for x in samples))
    if peak > 0.9:
        samples = [x / peak * 0.9 for x in samples]
    return samples


def _to_sound(samples: list[float]) -> pygame.mixer.Sound:
    buf = array.array("h")
    for s in samples:
        v = int(max(-1.0, min(1.0, s)) * 32767)
        buf.append(v)   # canal izquierdo
        buf.append(v)   # canal derecho
    return pygame.mixer.Sound(buffer=buf.tobytes())


# ------------------------------------------------------------------
# Gestor de sonido
# ------------------------------------------------------------------
class SoundManager:
    """
    Sintetiza una pequeña librería de SFX al arrancar y los reproduce
    por nombre (con pequeñas variantes aleatorias en los sonidos más
    repetidos, para que no suenen mecánicos), más una pista de ambiente
    de fondo en bucle. Si no hay dispositivo de audio disponible (o
    SFX_ENABLED/MUSIC_ENABLED son False en config/settings.py) se
    desactiva silenciosamente: nunca debe romper la partida por no poder
    sonar.
    """

    # Canal reservado en exclusiva para la música de fondo, para que los
    # SFX (que pygame reparte entre el resto de canales libres) nunca la
    # corten ni la pisen.
    MUSIC_CHANNEL_ID = 7

    def __init__(self) -> None:
        self.enabled = bool(getattr(cfg, "SFX_ENABLED", True))
        self.music_enabled = bool(getattr(cfg, "MUSIC_ENABLED", True))
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._variants: dict[str, list[pygame.mixer.Sound]] = {}
        self._music: Optional[pygame.mixer.Sound] = None
        self._music_channel: Optional[pygame.mixer.Channel] = None
        self._music_playing = False
        if not self.enabled and not self.music_enabled:
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2)
            if pygame.mixer.get_num_channels() <= self.MUSIC_CHANNEL_ID:
                pygame.mixer.set_num_channels(self.MUSIC_CHANNEL_ID + 1)
            if self.enabled:
                self._build_library()
            if self.music_enabled:
                self._build_music()
        except Exception:
            self.enabled = False
            self.music_enabled = False

    # ------------------------------------------------------------------
    # SFX
    # ------------------------------------------------------------------
    def _build_library(self) -> None:
        vol = float(getattr(cfg, "SFX_VOLUME", 0.8))

        # Carta repartida: chasquido breve de ruido filtrado. Varias
        # variantes con pequeñas diferencias de duración/volumen para que
        # no suene idéntico en cada reparto (docenas de veces por mano).
        self._variants["deal"] = [
            _to_sound(_noise_burst(random.uniform(0.042, 0.058),
                                    vol=random.uniform(0.26, 0.34) * vol))
            for _ in range(4)
        ]

        # Flip de la hole card: "snap" grave descendente
        self._sounds["flip"] = _to_sound(
            _tone_wave(560, 320, 0.10, vol=0.35 * vol, wave="square", noise=0.18)
        )

        # Ficha añadida / retirada de la apuesta — variantes con leves
        # cambios de tono, como fichas físicas distintas al apilarse.
        self._variants["chip"] = [
            _to_sound(_tone_wave(f0, f0 * 0.63, 0.05, vol=0.28 * vol, wave="square"))
            for f0 in (1420, 1500, 1580)
        ]
        self._sounds["chip_undo"] = _to_sound(
            _tone_wave(750, 520, 0.055, vol=0.26 * vol, wave="square")
        )

        # Click genérico de botón (fases sin acción de mano: apostar, deal…)
        self._sounds["button"] = _to_sound(
            _tone_wave(620, 720, 0.035, vol=0.20 * vol)
        )

        # Sonidos de acción del jugador, uno distinto por botón, en vez de
        # reutilizar todos el "click" genérico — así cada decisión se
        # "siente" un poco distinta, a juego con el color de su botón.
        self._sounds["act_hit"] = _to_sound(
            _tone_wave(520, 780, 0.05, vol=0.24 * vol, wave="sine")
        )
        self._sounds["act_stand"] = _to_sound(
            _tone_wave(460, 360, 0.08, vol=0.26 * vol, wave="square")
        )
        self._sounds["act_double"] = _to_sound(
            _sequence([440.0, 660.0], note_dur=0.05, vol=0.30 * vol, wave="square")
        )
        self._sounds["act_split"] = _to_sound(
            _mix(_tone_wave(520, 640, 0.07, vol=0.22 * vol),
                 _tone_wave(500, 380, 0.07, vol=0.22 * vol))
        )
        self._sounds["act_surrender"] = _to_sound(
            _tone_wave(480, 240, 0.16, vol=0.24 * vol, wave="sine", release=0.12)
        )

        # Resultados de ronda
        self._sounds["win"] = _to_sound(
            _sequence([523.25, 659.25, 784.0], note_dur=0.08, vol=0.40 * vol)
        )
        self._sounds["blackjack"] = _to_sound(
            _sequence([523.25, 659.25, 784.0, 1046.5], note_dur=0.09, vol=0.48 * vol)
        )
        # Logro desbloqueado: fanfarria corta, distinta de "win"/"blackjack"
        self._sounds["achievement"] = _to_sound(
            _sequence([392.0, 523.25, 659.25, 880.0], note_dur=0.07, vol=0.42 * vol)
        )
        self._sounds["bust"] = _to_sound(
            _tone_wave(220, 80, 0.35, vol=0.38 * vol, wave="square", noise=0.12, release=0.25)
        )
        self._sounds["push"] = _to_sound(
            _mix(_tone_wave(440, 440, 0.14, vol=0.28 * vol),
                 _tone_wave(440 * 1.5, 440 * 1.5, 0.14, vol=0.14 * vol))
        )

        # Rebarajado del zapato
        self._sounds["shuffle"] = _to_sound(_noise_burst(0.55, vol=0.20 * vol))

    def play(self, name: str) -> None:
        if not self.enabled:
            return
        variants = self._variants.get(name)
        snd = random.choice(variants) if variants else self._sounds.get(name)
        if snd is None:
            return
        try:
            snd.play()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Música de ambiente
    # ------------------------------------------------------------------
    def _build_music(self) -> None:
        music_vol = float(getattr(cfg, "MUSIC_VOLUME", 0.4))
        self._music = _to_sound(_ambient_track(duration=24.0, vol=0.55 * music_vol))
        self._music_channel = pygame.mixer.Channel(self.MUSIC_CHANNEL_ID)

    def start_music(self) -> None:
        """Arranca (o reanuda) la música de ambiente en bucle infinito.
        Si ya está sonando no hace nada."""
        if not self.music_enabled or self._music is None or self._music_channel is None:
            return
        try:
            if self._music_playing:
                return
            self._music_channel.play(self._music, loops=-1, fade_ms=1200)
            self._music_playing = True
        except Exception:
            pass

    def stop_music(self) -> None:
        if self._music_channel is None:
            return
        try:
            self._music_channel.fadeout(600)
        except Exception:
            pass
        self._music_playing = False

    def toggle_music(self) -> bool:
        """Silencia/reanuda la música. Devuelve el nuevo estado (sonando o no)."""
        if self._music_playing:
            self.stop_music()
        else:
            self.start_music()
        return self._music_playing

    # ------------------------------------------------------------------
    # Ajustes en caliente (Fase 16): la pantalla de Ajustes llama a estos
    # métodos directamente sobre la instancia real de SoundManager (se le
    # pasa por referencia desde Renderer → MainMenu → SettingsScreen) para
    # que el volumen se escuche cambiar AL INSTANTE mientras se arrastra
    # el slider, sin esperar a cerrar el menú.
    # ------------------------------------------------------------------
    def set_sfx_volume(self, v: float) -> None:
        """Volumen de efectos (0.0-1.0), aplicado como ganancia de
        reproducción sobre cada Sound ya generado -- no hace falta
        regenerar la librería."""
        v = max(0.0, min(1.0, v))
        for snd in self._sounds.values():
            try:
                snd.set_volume(v)
            except Exception:
                pass
        for variants in self._variants.values():
            for snd in variants:
                try:
                    snd.set_volume(v)
                except Exception:
                    pass

    def set_music_volume(self, v: float) -> None:
        """Volumen de música (0.0-1.0), aplicado como ganancia de
        reproducción sobre el canal reservado -- efecto inmediato aunque
        la música ya esté sonando."""
        v = max(0.0, min(1.0, v))
        if self._music_channel is not None:
            try:
                self._music_channel.set_volume(v)
            except Exception:
                pass

    def set_sfx_enabled(self, on: bool) -> None:
        """Activa/desactiva los efectos. Si se activan y la librería nunca
        llegó a construirse (estaban desactivados al arrancar), se
        construye ahora mismo."""
        if on and not self._sounds and not self._variants:
            try:
                if not pygame.mixer.get_init():
                    pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2)
                self._build_library()
            except Exception:
                return
        self.enabled = on

    def set_music_enabled(self, on: bool) -> None:
        """Activa/desactiva la música de ambiente. Si se activa y nunca
        llegó a construirse el buffer (estaba desactivada al arrancar),
        se construye ahora mismo antes de arrancarla."""
        self.music_enabled = on
        if on:
            if self._music is None or self._music_channel is None:
                try:
                    if not pygame.mixer.get_init():
                        pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2)
                    if pygame.mixer.get_num_channels() <= self.MUSIC_CHANNEL_ID:
                        pygame.mixer.set_num_channels(self.MUSIC_CHANNEL_ID + 1)
                    self._build_music()
                except Exception:
                    return
            self.start_music()
        else:
            self.stop_music()
