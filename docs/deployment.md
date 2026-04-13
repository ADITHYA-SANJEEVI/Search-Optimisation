# Deployment

## Local mode

The default local/demo mode does not require Docker or OpenSearch.

```powershell
pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File .\scripts\run_local.ps1
```

Useful local URLs:

- `http://localhost:8000/docs`
- `http://localhost:8000/demo`

## Optional OpenSearch mode

Use this only when validating the optional adapter path:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_opensearch.ps1
python .\scripts\opensearch_smoke_test.py
```

Stop it when done:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\stop_opensearch.ps1
```

## Environment variables

See `.env.example` for the supported runtime settings.

The most relevant toggles are:

- `AUTH_ENABLED`
- `API_KEYS`
- `RATE_LIMIT_ENABLED`
- `SEARCH_BACKEND`
- `OPENSEARCH_URL`
- `ANALYTICS_DB_PATH`
- `STT_PROVIDER`
- `VOICE_MOCK_ENABLED`

## Production-oriented notes

This repository is a production-oriented backend prototype, not a fully enterprise-ready deployment package.

Practical recommendations:

- run behind a reverse proxy or ingress
- use the REST contract as the stable integration surface for the Java backend
- enable auth and rate limiting in non-demo environments
- use OpenSearch only when you actually need that backend path
- keep Docker off when working only in the default in-memory mode
