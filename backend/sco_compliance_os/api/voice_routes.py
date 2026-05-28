"""Router /api/voice — STT (Whisper.cpp) + TTS (Piper) on-device.

Privacy hard requirement: tutto on-device, niente cloud STT/TTS.

Endpoint:
- POST /api/voice/transcribe  multipart audio file + language -> {text, duration_ms, model}
- POST /api/voice/synthesize  JSON {text, voice} -> audio/wav stream
- GET  /api/voice/voices      lista voci disponibili
- GET  /api/voice/status      diagnostica tooling (ffmpeg, whisper-cli, piper, modelli)

Pattern Conv. 44 lesson 1: NO --reload da shell ephemeral (zombie socket).
Pattern Conv. 44 lesson 2: CORS gia' coperto dal main.py per Tauri 2 origin.
Pattern Conv. 41: tracciatura puntuale ogni op (durata, modello, esito).
Pattern Conv. 46: smoke test E2E PRIMA del tag (curl POST con file wav reale).
"""

from __future__ import annotations

import io

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from sco_compliance_os.core.logging_setup import get_logger
from sco_compliance_os.services.voice import stt, tts

logger = get_logger(__name__)

router = APIRouter(prefix="/api/voice", tags=["voice"])


# ----- Schemi Pydantic -----


class TranscribeResponse(BaseModel):
    """Response trascrizione STT."""

    text: str = Field(..., description="Testo trascritto.")
    duration_ms: int = Field(..., description="Tempo elaborazione in millisecondi.")
    model: str = Field(..., description="Nome modello whisper usato.")
    language: str = Field(..., description="Lingua input (it/en/auto).")


class SynthesizeRequest(BaseModel):
    """Request sintesi TTS."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Testo da sintetizzare (max 2000 char per latency ragionevole).",
    )
    voice: str = Field(
        default="it_IT-paola-medium",
        description="ID voce piper. Default voce italiana femminile.",
    )


class VoiceListResponse(BaseModel):
    """Response lista voci disponibili."""

    voices: list[dict[str, str]] = Field(..., description="Lista voci con metadata.")


class StatusResponse(BaseModel):
    """Response diagnostica voice tooling."""

    stt: dict[str, bool] = Field(..., description="Disponibilita' tooling STT.")
    tts: dict[str, bool] = Field(..., description="Disponibilita' tooling TTS.")


# ----- Endpoint STT -----


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(
    audio: UploadFile = File(..., description="File audio (WebM Opus, WAV, MP3, M4A)."),
    language: str = Form(default="it", description="Lingua: it, en, auto."),
) -> TranscribeResponse:
    """Trascrive audio in testo on-device via whisper.cpp.

    Body multipart:
    - audio: file audio (WebM Opus da MediaRecorder browser, WAV, MP3, M4A)
    - language: codice lingua ISO 639-1 (default "it")

    Privacy: nessun dato lascia il dispositivo.
    """
    # Validazione lingua minima
    allowed_langs = {"it", "en", "auto", "fr", "de", "es", "pt"}
    if language not in allowed_langs:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language: {language}. Allowed: {sorted(allowed_langs)}",
        )

    # Validazione tipo file
    content_type = (audio.content_type or "").lower()
    if not (content_type.startswith("audio/") or content_type == "application/octet-stream"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid content_type: {content_type}. Expected audio/*.",
        )

    # Determina source_format dall'estensione o content_type
    filename = (audio.filename or "").lower()
    source_format = "webm"
    if filename.endswith(".wav") or "wav" in content_type:
        source_format = "wav"
    elif filename.endswith(".mp3") or "mp3" in content_type or "mpeg" in content_type:
        source_format = "mp3"
    elif filename.endswith(".m4a") or "mp4" in content_type:
        source_format = "m4a"
    elif filename.endswith(".ogg") or "ogg" in content_type:
        source_format = "ogg"
    elif filename.endswith(".opus") or "opus" in content_type:
        source_format = "opus"

    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio body")

    # Limite hard 25 MB (~25 min audio compresso)
    if len(audio_bytes) > 25 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="Audio too large (>25MB). Split in chunks client-side.",
        )

    logger.info(
        "voice.api.transcribe.start",
        language=language,
        source_format=source_format,
        bytes=len(audio_bytes),
        content_type=content_type,
    )

    try:
        result = await stt.transcribe(
            audio_bytes,
            language=language,
            source_format=source_format,
        )
    except FileNotFoundError as exc:
        # Tooling mancante (ffmpeg o whisper-cli)
        logger.warning("voice.api.transcribe.tooling_missing", error=str(exc))
        raise HTTPException(
            status_code=503,
            detail=(
                f"Voice STT tooling unavailable: {exc}. "
                "Ensure ffmpeg and whisper-cli are installed."
            ),
        ) from exc
    except RuntimeError as exc:
        msg = str(exc).lower()
        if "not found" in msg or "binary" in msg or "ffmpeg" in msg:
            logger.warning("voice.api.transcribe.tooling_missing", error=str(exc))
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        logger.error("voice.api.transcribe.runtime_error", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return TranscribeResponse(
        text=result.text,
        duration_ms=result.duration_ms,
        model=result.model,
        language=result.language,
    )


# ----- Endpoint TTS -----


@router.post("/synthesize")
async def synthesize_text(req: SynthesizeRequest) -> StreamingResponse:
    """Sintetizza testo in audio WAV on-device via piper.

    Body JSON {text, voice}.

    Returns audio/wav binary stream.

    Privacy: nessun testo o audio lascia il dispositivo.
    """
    try:
        result = await tts.synthesize(req.text, voice=req.voice)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        logger.warning("voice.api.synthesize.tooling_missing", error=str(exc))
        raise HTTPException(
            status_code=503,
            detail=(f"Voice TTS tooling unavailable: {exc}. Ensure piper binary is installed."),
        ) from exc
    except RuntimeError as exc:
        # RuntimeError "binary not found" -> 503 (tooling missing).
        # Altri RuntimeError -> 500 (errore esecuzione).
        msg = str(exc).lower()
        if "not found" in msg or "binary" in msg:
            logger.warning("voice.api.synthesize.tooling_missing", error=str(exc))
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        logger.error("voice.api.synthesize.runtime_error", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    headers = {
        "X-Voice-Id": result.voice,
        "X-Voice-Language": result.language,
        "X-Synthesis-Duration-Ms": str(result.duration_ms),
        "Content-Disposition": f'inline; filename="synthesis_{result.voice}.wav"',
    }
    return StreamingResponse(
        io.BytesIO(result.wav_bytes),
        media_type="audio/wav",
        headers=headers,
    )


# ----- Diagnostica -----


@router.get("/voices", response_model=VoiceListResponse)
async def list_available_voices() -> VoiceListResponse:
    """Lista voci TTS disponibili con metadata + flag installed."""
    return VoiceListResponse(voices=tts.list_voices())


@router.get("/status", response_model=StatusResponse)
async def voice_status() -> StatusResponse:
    """Diagnostica tooling voice (binari + modelli presenti)."""
    return StatusResponse(
        stt=await stt.is_available(),
        tts=await tts.is_available(),
    )
