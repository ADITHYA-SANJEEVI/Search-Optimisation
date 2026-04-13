$ErrorActionPreference = "Stop"

docker compose stop
Write-Host "Stopped optional Docker services for this repo."

docker container prune -f
docker image prune -a -f
docker builder prune -f
docker volume prune -f

Write-Host "Extended Docker cleanup complete."
Write-Host "This also removed globally unused Docker volumes."
