$ErrorActionPreference = "Stop"
docker compose up -d opensearch
Write-Host "OpenSearch startup requested. Validate with scripts/opensearch_smoke_test.py."
