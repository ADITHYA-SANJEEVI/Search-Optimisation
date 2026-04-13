"""Voice transcription adapter interface and mock implementation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tempfile

from app.core.config import settings
from app.core.errors import ServiceError
from app.utils.text import remove_fillers


@dataclass(slots=True)
class TranscriptionResult:
    transcript: str
    confidence: float


class TranscriptionAdapter:
    def transcribe(self, filename: str, content_type: str, payload: bytes) -> TranscriptionResult:
        raise NotImplementedError


class WhisperTranscriptionAdapter(TranscriptionAdapter):
    """Transcription using faster-whisper when installed and cached."""

    def __init__(self) -> None:
        self._model = None
        try:
            from faster_whisper import WhisperModel  # type: ignore

            self._model = WhisperModel(
                settings.whisper_model_name,
                device="cpu",
                compute_type=settings.whisper_compute_type,
                download_root=settings.whisper_download_root,
            )
        except Exception as exc:  # pragma: no cover
            raise ServiceError(
                "stt_unavailable",
                "Whisper transcription adapter could not be initialized",
                status_code=503,
                details={"reason": str(exc)},
            ) from exc

    def transcribe(self, filename: str, content_type: str, payload: bytes) -> TranscriptionResult:
        if self._model is None:
            raise ServiceError("stt_unavailable", "Whisper transcription model is not loaded", status_code=503)
        suffix = Path(filename).suffix or ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(payload)
            temp_path = temp_file.name
        try:
            segments, info = self._model.transcribe(
                temp_path,
                beam_size=5,
                vad_filter=True,
                language=settings.whisper_language,
            )
            transcript = " ".join(segment.text.strip() for segment in segments).strip()
            transcript = remove_fillers(transcript)
            if not transcript:
                raise ServiceError("stt_empty_transcript", "Whisper returned an empty transcript", status_code=422)
            confidence = 0.0
            if hasattr(info, "language_probability") and info.language_probability is not None:
                confidence = float(info.language_probability)
            return TranscriptionResult(transcript=transcript, confidence=confidence)
        finally:
            try:
                Path(temp_path).unlink(missing_ok=True)
            except Exception:
                pass


class MockTranscriptionAdapter(TranscriptionAdapter):
    """Offline-friendly adapter that derives a transcript from the filename."""

    def transcribe(self, filename: str, content_type: str, payload: bytes) -> TranscriptionResult:
        if not settings.voice_mock_enabled:
            raise ServiceError(
                "stt_unavailable",
                "Speech-to-text adapter is unavailable",
                status_code=503,
                details={"content_type": content_type},
            )
        stem = Path(filename).stem.replace("_", " ").replace("-", " ")
        transcript = remove_fillers(stem)
        if not transcript:
            raise ServiceError(
                "stt_unavailable",
                "Voice transcript could not be derived by the mock adapter",
                status_code=503,
                details={"filename": filename},
            )
        return TranscriptionResult(transcript=transcript, confidence=0.64)


def build_transcription_adapter() -> TranscriptionAdapter:
    if settings.stt_provider.lower() == "whisper":
        try:
            return WhisperTranscriptionAdapter()
        except ServiceError:
            if not settings.voice_mock_enabled:
                raise
    return MockTranscriptionAdapter()
