$ErrorActionPreference = "Stop"

if (-not $env:API_KEYS) {
    $env:API_KEYS = "dev-search-key"
}

if (-not $env:AUTH_ENABLED) {
    $env:AUTH_ENABLED = "false"
}

if (-not $env:STT_PROVIDER) {
    $env:STT_PROVIDER = "whisper"
}

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
