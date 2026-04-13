"""Environment-backed application settings."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _float(name: str, default: float) -> float:
    raw = os.getenv(name)
    return float(raw) if raw is not None else default


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw is not None else default


@dataclass(slots=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Aastrika Sphere Search Service")
    environment: str = os.getenv("ENVIRONMENT", "development")
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = _int("PORT", 8000)
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    api_prefix: str = os.getenv("API_PREFIX", "/api/v1")
    schema_version: str = os.getenv("SCHEMA_VERSION", "1.0.0")
    api_key_header_name: str = os.getenv("API_KEY_HEADER_NAME", "X-API-Key")
    api_keys_raw: str = os.getenv("API_KEYS", "dev-search-key")
    auth_enabled: bool = _bool("AUTH_ENABLED", False)
    rate_limit_enabled: bool = _bool("RATE_LIMIT_ENABLED", False)
    rate_limit_requests: int = _int("RATE_LIMIT_REQUESTS", 60)
    rate_limit_window_seconds: int = _int("RATE_LIMIT_WINDOW_SECONDS", 60)
    max_request_bytes: int = _int("MAX_REQUEST_BYTES", 1_048_576)
    max_audio_upload_bytes: int = _int("MAX_AUDIO_UPLOAD_BYTES", 5_242_880)
    safe_error_mode: bool = _bool("SAFE_ERROR_MODE", True)
    bootstrap_sample_data: bool = _bool("BOOTSTRAP_SAMPLE_DATA", True)
    sample_data_path: str = os.getenv("SAMPLE_DATA_PATH", "sample_data/courses.json")
    search_backend: str = os.getenv("SEARCH_BACKEND", "inmemory")
    opensearch_url: str = os.getenv("OPENSEARCH_URL", "http://localhost:9200")
    opensearch_index: str = os.getenv("OPENSEARCH_INDEX", "aastrika-courses-v1")
    opensearch_verify_certs: bool = _bool("OPENSEARCH_VERIFY_CERTS", False)
    opensearch_timeout_seconds: int = _int("OPENSEARCH_TIMEOUT_SECONDS", 10)
    enable_semantic_search: bool = _bool("ENABLE_SEMANTIC_SEARCH", True)
    enable_indic_transliteration: bool = _bool("ENABLE_INDIC_TRANSLITERATION", True)
    enable_debug_payloads: bool = _bool("ENABLE_DEBUG_PAYLOADS", True)
    voice_mock_enabled: bool = _bool("VOICE_MOCK_ENABLED", True)
    stt_provider: str = os.getenv("STT_PROVIDER", "mock")
    whisper_model_name: str = os.getenv("WHISPER_MODEL_NAME", "tiny")
    whisper_compute_type: str = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
    whisper_download_root: str = os.getenv("WHISPER_DOWNLOAD_ROOT", ".cache/whisper")
    whisper_language: str | None = os.getenv("WHISPER_LANGUAGE")
    analytics_enabled: bool = _bool("ANALYTICS_ENABLED", True)
    analytics_db_path: str = os.getenv("ANALYTICS_DB_PATH", "data/analytics.db")
    max_query_length: int = _int("MAX_QUERY_LENGTH", 240)
    default_page_size: int = _int("DEFAULT_PAGE_SIZE", 10)
    max_page_size: int = _int("MAX_PAGE_SIZE", 25)
    autocorrect_confidence_threshold: float = _float("AUTOCORRECT_CONFIDENCE_THRESHOLD", 0.90)
    show_results_for_confidence_threshold: float = _float("SHOW_RESULTS_FOR_CONFIDENCE_THRESHOLD", 0.96)
    did_you_mean_similarity_ceiling: float = _float("DID_YOU_MEAN_SIMILARITY_CEILING", 0.985)
    min_candidate_score: float = _float("MIN_CANDIDATE_SCORE", 0.35)
    semantic_rescue_threshold: float = _float("SEMANTIC_RESCUE_THRESHOLD", 0.28)
    fuzzy_rescue_threshold: float = _float("FUZZY_RESCUE_THRESHOLD", 0.78)
    weights: dict[str, float] = field(
        default_factory=lambda: {
            "bm25": _float("WEIGHT_BM25", 0.32),
            "title_bm25": _float("WEIGHT_TITLE_BM25", 0.18),
            "fuzzy": _float("WEIGHT_FUZZY", 0.14),
            "semantic": _float("WEIGHT_SEMANTIC", 0.18),
            "phrase": _float("WEIGHT_PHRASE", 0.08),
            "phonetic": _float("WEIGHT_PHONETIC", 0.04),
            "popularity": _float("WEIGHT_POPULARITY", 0.03),
            "recency": _float("WEIGHT_RECENCY", 0.01),
            "language_boost": _float("WEIGHT_LANGUAGE_BOOST", 0.06),
        }
    )
    allowed_audio_types: tuple[str, ...] = (
        "audio/wav",
        "audio/x-wav",
        "audio/mpeg",
        "audio/mp3",
        "audio/ogg",
        "audio/webm",
        "audio/mp4",
        "audio/x-m4a",
    )

    @property
    def api_keys(self) -> set[str]:
        return {item.strip() for item in self.api_keys_raw.split(",") if item.strip()}


settings = Settings()
