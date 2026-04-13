$ErrorActionPreference = "Stop"

docker compose stop
Write-Host "Stopped optional Docker services for this repo."

docker container prune -f
docker image prune -a -f
docker builder prune -f

Write-Host "Safe Docker cleanup complete."
Write-Host "Stopped containers, unused images, and build cache were removed."
Write-Host "Unused volumes were left intact."
