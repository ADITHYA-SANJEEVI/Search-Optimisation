# Docker Cleanup

Docker and OpenSearch are optional for this repository. The default local backend mode is the in-memory adapter, so Docker can be stopped completely when you are not validating the optional OpenSearch path.

## Safe cleanup

Use this when you want to reclaim space without touching Docker volumes:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\stop_opensearch.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\docker_cleanup_safe.ps1
```

What it does:

- stops the repo's Docker services
- removes stopped containers
- removes unused images
- removes build cache

What it does not do:

- does not remove Docker volumes
- does not affect the default in-memory backend mode

## More aggressive cleanup

Use this only if you explicitly want to remove globally unused Docker volumes too:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\docker_cleanup_with_volumes.ps1
```

This is more destructive because Docker volumes may contain cached data from other local projects. It is still limited to unused volumes, but it is not repo-specific.

## Optional OpenSearch flow

Start OpenSearch only when you actually need it:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_opensearch.ps1
python .\scripts\opensearch_smoke_test.py
```

When finished:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\stop_opensearch.ps1
```
