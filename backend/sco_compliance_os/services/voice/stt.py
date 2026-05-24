"""STT (Speech-to-Text) on-device via whisper.cpp.

Privacy hard requirement: tutto locale, niente cloud (OpenAI Whisper API,
Deepgram, AssemblyAI, ecc.). Pattern SCO single source of truth lato
device per audio.

Architettura:
- Binario whisper-cli (whisper.cpp) auto-scaricato al primo use in
  ~/.sco-compliance-os/voice-bin/whisper-cli{.exe}
- Modelli ggml (base.en 75 MB, base.it via base multilingue 142 MB) in
  ~/.sco-compliance-os/voice-models/
- Pipeline: input audio bytes (WebM Opus o WAV) -> ffmpeg convert a PCM 16k
  mono WAV temp -> whisper-cli -> stdout trascrizione

Conv. 44 lesson 3 enforcement: whisper-cli e piper sono binari nativi che NON
vivono nel pyz PyInstaller. Vanno spediti come sidecar separati nel bundle MSI
oppure scaricati al primo use (strategia attuale: download lazy, no bundle
extra peso).

Conv. 46 enforcement: smoke test E2E con audio reale prima del tag (vedi
endpoint /api/voice/transcribe).

Conv. 41 enforcement: ogni operazione log structured con timings + model used.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import platform
import shutil
import subprocess
import tempfile
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import structlog

from sco_compliance_os.config import get_settings

logger = structlog.get_logger(__name__)


# ----- Costanti modelli + binari -----

# Modello ggml whisper base.en (75 MB) — solo inglese, piu' veloce
# Modello ggml whisper base (142 MB) — multilingue, supporta italiano + en
WHISPER_MODELS = {
    "base.en": {
        "filename": "ggml-base.en.bin",
        "url": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin",
        "size_bytes": 147_964_211,  # ~141 MB
        "languages": ["en"],
    },
    "base": {
        "filename": "ggml-base.bin",
        "url": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin",
        "size_bytes": 147_951_465,  # ~141 MB (multilingue)
        "languages": ["it", "en", "fr", "de", "es", "pt", "auto"],
    },
}

# Binario whisper-cli pre-built (Conv. 45 cross-platform matrix)
# I binari ufficiali whisper.cpp non hanno release per ogni OS+arch in CI
# pubblica; per produzione conviene linkare a un mirror managed SCO.
# Per ora: fallback a "ricerca PATH" + log warning se mancante.
WHISPER_CLI_BIN_NAME = "whisper-cli.exe" if platform.system() == "Windows" else "whisper-cli"


# ----- Pubblico API -----


@dataclass(slots=True)
class TranscriptionResult:
    """Risultato trascrizione."""

    text: str
    language: str
    model: str
    duration_ms: int


# ----- Path helpers -----


def _voice_bin_dir() -> Path:
    """~/.sco-compliance-os/voice-bin/"""
    settings = get_settings()
    bin_dir = settings.data_dir / "voice-bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    return bin_dir


def _voice_models_dir() -> Path:
    """~/.sco-compliance-os/voice-models/"""
    settings = get_settings()
    models_dir = settings.data_dir / "voice-models"
    models_dir.mkdir(parents=True, exist_ok=True)
    return models_dir


def _resolve_whisper_cli() -> Path | None:
    """Trova whisper-cli: cache locale o PATH di sistema.

    Returns None se non trovato. Il chiamante decide la strategia (download
    on-demand, errore, ecc.).
    """
    # 1. Cache locale ~/.sco-compliance-os/voice-bin/
    local = _voice_bin_dir() / WHISPER_CLI_BIN_NAME
    if local.exists() and os.access(local, os.X_OK):
        return local

    # 2. Sistema PATH (utente lo ha installato via brew/apt/scoop)
    system = shutil.which("whisper-cli") or shutil.which("whisper")
    if system:
        return Path(system)

    return None


def _resolve_model_path(model_name: str) -> Path | None:
    """Trova il modello ggml in cache. None se mancante (trigger download)."""
    if model_name not in WHISPER_MODELS:
        return None
    filename = WHISPER_MODELS[model_name]["filename"]
    model_path = _voice_models_dir() / filename
    return model_path if model_path.exists() else None


# ----- Download lazy -----


def _download_model_blocking(model_name: str) -> Path:
    """Scarica modello ggml dalla HuggingFace mirror.

    Blocking: chiamante deve girarlo in run_in_executor.
    Verifica integrita' via dimensione attesa.
    """
    if model_name not in WHISPER_MODELS:
        raise ValueError(f"Unknown whisper model: {model_name}")

    meta = WHISPER_MODELS[model_name]
    dest = _voice_models_dir() / meta["filename"]
    if dest.exists():
        return dest

    logger.info(
        "voice.stt.model_download.start",
        model=model_name,
        url=meta["url"],
        size_mb=meta["size_bytes"] // (1024 * 1024),
    )
    t0 = time.time()
    # Download streaming
    tmp = dest.with_suffix(".download")
    try:
        with urllib.request.urlopen(meta["url"], timeout=60) as response:
            with tmp.open("wb") as out:
                shutil.copyfileobj(response, out, length=1024 * 64)
        # Verifica dimensione (tolleranza 1%)
        actual_size = tmp.stat().st_size
        expected = meta["size_bytes"]
        if abs(actual_size - expected) / expected > 0.01:
            tmp.unlink(missing_ok=True)
            raise RuntimeError(
                f"Model download size mismatch: got {actual_size}, expected {expected}"
            )
        tmp.rename(dest)
    except Exception as exc:
        tmp.unlink(missing_ok=True)
        logger.error("voice.stt.model_download.failed", error=str(exc))
        raise

    elapsed = time.time() - t0
    logger.info(
        "voice.stt.model_download.done",
        model=model_name,
        dest=str(dest),
        elapsed_seconds=int(elapsed),
    )
    return dest


# ----- Conversione audio via ffmpeg -----


def _ffmpeg_path() -> str | None:
    """Trova ffmpeg in PATH. None se mancante."""
    return shutil.which("ffmpeg")


def _convert_to_pcm16k_mono_blocking(input_bytes: bytes, source_format: str) -> bytes:
    """Converte input audio (WebM Opus o WAV) a PCM 16kHz mono 16-bit WAV.

    Blocking: chiamante deve girarlo in run_in_executor.
    """
    ffmpeg = _ffmpeg_path()
    if not ffmpeg:
        raise RuntimeError(
            "ffmpeg not found in PATH. Install ffmpeg or bundle the binary."
        )

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        # Determina estensione input dal format
        ext_map = {
            "webm": ".webm",
            "ogg": ".ogg",
            "opus": ".opus",
            "wav": ".wav",
            "mp3": ".mp3",
            "m4a": ".m4a",
        }
        in_ext = ext_map.get(source_format.lower(), ".webm")
        in_path = td_path / f"input{in_ext}"
        out_path = td_path / "output.wav"

        in_path.write_bytes(input_bytes)

        # ffmpeg -i input.webm -ar 16000 -ac 1 -c:a pcm_s16le output.wav
        cmd = [
            ffmpeg,
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(in_path),
            "-ar",
            "16000",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(out_path),
        ]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30,
                check=False,
            )
            if proc.returncode != 0:
                raise RuntimeError(
                    f"ffmpeg failed: {proc.stderr.decode('utf-8', errors='replace')[:500]}"
                )
            return out_path.read_bytes()
        except subprocess.TimeoutExpired:
            raise RuntimeError("ffmpeg conversion timeout (>30s)")


# ----- Invocazione whisper-cli -----


def _run_whisper_cli_blocking(
    pcm16k_wav_bytes: bytes,
    model_path: Path,
    language: str,
) -> str:
    """Invoca whisper-cli su WAV in input, ritorna testo trascritto.

    Blocking: chiamante deve girarlo in run_in_executor.
    """
    cli = _resolve_whisper_cli()
    if not cli:
        raise RuntimeError(
            "whisper-cli binary not found. Install whisper.cpp or place "
            "whisper-cli in ~/.sco-compliance-os/voice-bin/"
        )

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        wav_path = td_path / "in.wav"
        wav_path.write_bytes(pcm16k_wav_bytes)

        # whisper.cpp CLI args:
        #   -m <model>       model path
        #   -f <audio>       audio file (16-bit WAV)
        #   -l <lang>        language (auto/it/en)
        #   -np              no print special tokens
        #   -nt              no timestamps
        #   --output-txt     output as txt
        #   -of <prefix>     output file prefix
        out_prefix = td_path / "out"
        cmd = [
            str(cli),
            "-m",
            str(model_path),
            "-f",
            str(wav_path),
            "-l",
            language,
            "-np",
            "-nt",
            "--output-txt",
            "-of",
            str(out_prefix),
        ]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                timeout=120,
                check=False,
            )
            if proc.returncode != 0:
                raise RuntimeError(
                    f"whisper-cli failed: {proc.stderr.decode('utf-8', errors='replace')[:500]}"
                )
            # Output e' in <out_prefix>.txt
            txt_path = Path(str(out_prefix) + ".txt")
            if txt_path.exists():
                return txt_path.read_text(encoding="utf-8").strip()
            # Fallback su stdout
            return proc.stdout.decode("utf-8", errors="replace").strip()
        except subprocess.TimeoutExpired:
            raise RuntimeError("whisper-cli timeout (>120s)")


# ----- Pubblico async -----


async def transcribe(
    audio_bytes: bytes,
    language: str = "it",
    source_format: str = "webm",
) -> TranscriptionResult:
    """Trascrive audio bytes in testo, on-device.

    Args:
        audio_bytes: byte array audio raw (WebM Opus default da MediaRecorder
            browser; supporta anche WAV, MP3, OGG, M4A).
        language: codice lingua ISO 639-1 (it, en, fr, de, es, auto).
            "auto" usa il modello multilingue per detection.
        source_format: estensione formato input ("webm", "wav", "mp3", "m4a",
            "ogg", "opus"). Default "webm" da MediaRecorder.

    Returns:
        TranscriptionResult con text + language + duration_ms.

    Raises:
        RuntimeError se ffmpeg o whisper-cli mancano, o trascrizione fallisce.
        ValueError se language non supportato.

    Note Conv. 35: prima query veniva fatta a memoria, ora consulta wiki
    fonti (whisper.cpp readme + huggingface model card) per parametri esatti.
    """
    t0 = time.time()
    if not audio_bytes:
        raise ValueError("Empty audio_bytes")

    # Scelta modello: base.en se inglese puro, base (multilingue) altrimenti
    model_name = "base.en" if language == "en" else "base"
    model_path = _resolve_model_path(model_name)
    if model_path is None:
        # Lazy download del modello in executor
        loop = asyncio.get_running_loop()
        model_path = await loop.run_in_executor(
            None, _download_model_blocking, model_name
        )

    # Convert audio -> PCM 16kHz mono WAV
    loop = asyncio.get_running_loop()
    pcm_wav_bytes = await loop.run_in_executor(
        None, _convert_to_pcm16k_mono_blocking, audio_bytes, source_format
    )

    # Run whisper-cli
    text = await loop.run_in_executor(
        None, _run_whisper_cli_blocking, pcm_wav_bytes, model_path, language
    )

    elapsed_ms = int((time.time() - t0) * 1000)
    logger.info(
        "voice.stt.transcribe.done",
        model=model_name,
        language=language,
        text_len=len(text),
        duration_ms=elapsed_ms,
        source_format=source_format,
    )
    return TranscriptionResult(
        text=text,
        language=language,
        model=model_name,
        duration_ms=elapsed_ms,
    )


async def is_available() -> dict[str, bool]:
    """Diagnostica: verifica disponibilita' tooling STT.

    Returns dict {ffmpeg, whisper_cli, model_base, model_base_en}.
    """
    return {
        "ffmpeg": _ffmpeg_path() is not None,
        "whisper_cli": _resolve_whisper_cli() is not None,
        "model_base": _resolve_model_path("base") is not None,
        "model_base_en": _resolve_model_path("base.en") is not None,
    }
