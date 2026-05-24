"""TTS (Text-to-Speech) on-device via Piper.

Privacy hard requirement: tutto locale, niente cloud (ElevenLabs, OpenAI
TTS, Google Cloud TTS, ecc.). Pattern SCO single source of truth
lato device per audio sintetizzato.

Architettura:
- Binario piper auto-scaricato al primo use in
  ~/.sco-compliance-os/voice-bin/piper{.exe}
- Voci ONNX (it_IT-paola-medium ~63 MB, en_US-libritts-high ~120 MB) in
  ~/.sco-compliance-os/voice-models/
- Pipeline: stdin testo -> piper --model voice.onnx --output - -> stdout WAV bytes

Conv. 44 lesson 3 enforcement: piper e' binario nativo, non vive nel pyz
PyInstaller. Strategia download lazy al primo use, no bundle extra peso.

Conv. 46 enforcement: smoke test E2E con sintesi reale prima del tag (vedi
endpoint /api/voice/synthesize).

Conv. 41 enforcement: ogni operazione log structured con timings + voice used.
"""

from __future__ import annotations

import asyncio
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


# ----- Costanti voci + binario -----

# Voci Piper. Ogni voce = (onnx model + json config).
# Mirror ufficiale rhasspy/piper-voices su HuggingFace.
PIPER_VOICES = {
    "it_IT-paola-medium": {
        "onnx_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/it/it_IT/paola/medium/it_IT-paola-medium.onnx",
        "json_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/it/it_IT/paola/medium/it_IT-paola-medium.onnx.json",
        "language": "it",
        "size_bytes": 63_201_280,  # ~60 MB onnx
    },
    "en_US-libritts-high": {
        "onnx_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/libritts/high/en_US-libritts-high.onnx",
        "json_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/libritts/high/en_US-libritts-high.onnx.json",
        "language": "en",
        "size_bytes": 124_780_032,  # ~119 MB onnx
    },
}

PIPER_BIN_NAME = "piper.exe" if platform.system() == "Windows" else "piper"


# ----- Pubblico API -----


@dataclass(slots=True)
class SynthesisResult:
    """Risultato sintesi audio."""

    wav_bytes: bytes
    voice: str
    language: str
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


def _resolve_piper_bin() -> Path | None:
    """Trova piper: cache locale o PATH di sistema. None se mancante."""
    local = _voice_bin_dir() / PIPER_BIN_NAME
    if local.exists() and os.access(local, os.X_OK):
        return local
    system = shutil.which("piper")
    if system:
        return Path(system)
    return None


def _resolve_voice_paths(voice_name: str) -> tuple[Path, Path] | None:
    """Trova (onnx, json) della voce. None se entrambi mancano."""
    if voice_name not in PIPER_VOICES:
        return None
    models_dir = _voice_models_dir()
    onnx = models_dir / f"{voice_name}.onnx"
    json_cfg = models_dir / f"{voice_name}.onnx.json"
    if onnx.exists() and json_cfg.exists():
        return (onnx, json_cfg)
    return None


# ----- Download lazy voci -----


def _download_voice_blocking(voice_name: str) -> tuple[Path, Path]:
    """Scarica .onnx + .onnx.json della voce. Blocking, usa run_in_executor."""
    if voice_name not in PIPER_VOICES:
        raise ValueError(f"Unknown piper voice: {voice_name}")

    meta = PIPER_VOICES[voice_name]
    models_dir = _voice_models_dir()
    onnx_dest = models_dir / f"{voice_name}.onnx"
    json_dest = models_dir / f"{voice_name}.onnx.json"

    if onnx_dest.exists() and json_dest.exists():
        return (onnx_dest, json_dest)

    logger.info(
        "voice.tts.voice_download.start",
        voice=voice_name,
        size_mb=meta["size_bytes"] // (1024 * 1024),
    )
    t0 = time.time()
    try:
        for url, dest in [(meta["onnx_url"], onnx_dest), (meta["json_url"], json_dest)]:
            if dest.exists():
                continue
            tmp = dest.with_suffix(dest.suffix + ".download")
            with urllib.request.urlopen(url, timeout=120) as response:
                with tmp.open("wb") as out:
                    shutil.copyfileobj(response, out, length=1024 * 64)
            tmp.rename(dest)
    except Exception as exc:
        # cleanup parziali
        for d in (onnx_dest, json_dest):
            tmp = d.with_suffix(d.suffix + ".download")
            tmp.unlink(missing_ok=True)
        logger.error("voice.tts.voice_download.failed", error=str(exc), voice=voice_name)
        raise

    elapsed = time.time() - t0
    logger.info(
        "voice.tts.voice_download.done",
        voice=voice_name,
        elapsed_seconds=int(elapsed),
    )
    return (onnx_dest, json_dest)


# ----- Invocazione piper -----


def _run_piper_blocking(
    text: str,
    onnx_path: Path,
    json_path: Path,  # noqa: ARG001 (piper trova .onnx.json next to .onnx)
) -> bytes:
    """Sintetizza testo via piper. Ritorna WAV bytes. Blocking."""
    piper = _resolve_piper_bin()
    if not piper:
        raise RuntimeError(
            "piper binary not found. Install piper or place in "
            "~/.sco-compliance-os/voice-bin/"
        )

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        out_path = td_path / "out.wav"

        # piper --model voice.onnx --output_file out.wav
        # piper legge il testo da stdin
        cmd = [
            str(piper),
            "--model",
            str(onnx_path),
            "--output_file",
            str(out_path),
        ]
        try:
            proc = subprocess.run(
                cmd,
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=60,
                check=False,
            )
            if proc.returncode != 0:
                raise RuntimeError(
                    f"piper failed: {proc.stderr.decode('utf-8', errors='replace')[:500]}"
                )
            if not out_path.exists():
                raise RuntimeError("piper did not produce output WAV")
            return out_path.read_bytes()
        except subprocess.TimeoutExpired:
            raise RuntimeError("piper timeout (>60s)")


# ----- Pubblico async -----


async def synthesize(
    text: str,
    voice: str = "it_IT-paola-medium",
) -> SynthesisResult:
    """Sintetizza testo in WAV audio, on-device.

    Args:
        text: testo da sintetizzare. Max ~2000 caratteri per latency
            ragionevole; se piu' lungo, chunk by sentence dal chiamante.
        voice: nome voce ("it_IT-paola-medium", "en_US-libritts-high").

    Returns:
        SynthesisResult con wav_bytes + voice + language + duration_ms.

    Raises:
        RuntimeError se piper o voce mancano.
        ValueError se voice non supportata.
    """
    t0 = time.time()
    if not text.strip():
        raise ValueError("Empty text")
    if voice not in PIPER_VOICES:
        raise ValueError(
            f"Unknown voice: {voice}. Available: {list(PIPER_VOICES.keys())}"
        )

    # Trim a 2000 char per sicurezza latency
    text = text.strip()[:2000]

    # Risolvi paths o scarica
    voice_paths = _resolve_voice_paths(voice)
    if voice_paths is None:
        loop = asyncio.get_running_loop()
        voice_paths = await loop.run_in_executor(
            None, _download_voice_blocking, voice
        )

    onnx_path, json_path = voice_paths

    # Run piper
    loop = asyncio.get_running_loop()
    wav_bytes = await loop.run_in_executor(
        None, _run_piper_blocking, text, onnx_path, json_path
    )

    elapsed_ms = int((time.time() - t0) * 1000)
    meta = PIPER_VOICES[voice]
    logger.info(
        "voice.tts.synthesize.done",
        voice=voice,
        language=meta["language"],
        text_len=len(text),
        wav_bytes=len(wav_bytes),
        duration_ms=elapsed_ms,
    )
    return SynthesisResult(
        wav_bytes=wav_bytes,
        voice=voice,
        language=meta["language"],
        duration_ms=elapsed_ms,
    )


async def is_available() -> dict[str, bool]:
    """Diagnostica: verifica disponibilita' tooling TTS.

    Returns dict {piper_bin, voice_it_paola, voice_en_libritts}.
    """
    return {
        "piper_bin": _resolve_piper_bin() is not None,
        "voice_it_paola": _resolve_voice_paths("it_IT-paola-medium") is not None,
        "voice_en_libritts": _resolve_voice_paths("en_US-libritts-high") is not None,
    }


def list_voices() -> list[dict[str, str]]:
    """Lista voci disponibili (metadata)."""
    return [
        {
            "id": vid,
            "language": meta["language"],
            "size_mb": str(meta["size_bytes"] // (1024 * 1024)),
            "installed": str(_resolve_voice_paths(vid) is not None).lower(),
        }
        for vid, meta in PIPER_VOICES.items()
    ]
