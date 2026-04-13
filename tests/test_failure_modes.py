from __future__ import annotations

from app.core.config import settings
from app.voice.transcription import WhisperTranscriptionAdapter, build_transcription_adapter


def test_empty_query_returns_structured_error(client) -> None:
    response = client.post("/api/v1/search", json={"query": "  "})
    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "empty_query"


def test_voice_endpoint_returns_search_payload(client) -> None:
    response = client.post(
        "/api/v1/search/voice?preferred_language=Hindi",
        files={"file": ("pph_primary_management.wav", b"fake-audio", "audio/wav")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["degraded"] is False
    assert payload["search_response"]["results"][0]["group_id"] == "postpartum-hemorrhage"


def test_voice_endpoint_accepts_codec_suffixed_webm_content_type(client) -> None:
    response = client.post(
        "/api/v1/search/voice",
        files={"file": ("pph_primary_management.webm", b"fake-audio", "audio/webm;codecs=opus")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["degraded"] is False
    assert payload["search_response"]["results"][0]["group_id"] == "postpartum-hemorrhage"


def test_voice_endpoint_rejects_unsupported_format(client) -> None:
    response = client.post(
        "/api/v1/search/voice",
        files={"file": ("query.txt", b"not-audio", "text/plain")},
    )
    assert response.status_code == 415
    payload = response.json()
    assert payload["error"]["code"] == "unsupported_audio_type"


def test_whisper_adapter_initializes_when_enabled() -> None:
    previous_provider = settings.stt_provider
    previous_mock = settings.voice_mock_enabled
    settings.stt_provider = "whisper"
    settings.voice_mock_enabled = False
    try:
        adapter = build_transcription_adapter()
        assert isinstance(adapter, WhisperTranscriptionAdapter)
    finally:
        settings.stt_provider = previous_provider
        settings.voice_mock_enabled = previous_mock
