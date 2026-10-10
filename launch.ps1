[CmdletBinding()]
param(
    [ValidateSet("start", "stop", "restart", "status", "validate")]
    [string]$Action = "start",

    [ValidateSet("inmemory", "opensearch")]
    [string]$Backend = "inmemory",

    [ValidateRange(1, 65535)]
    [int]$Port = 8000,

    [switch]$NoBrowser,
    [switch]$Foreground
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$RuntimeDir = Join-Path $Root "artifacts\runtime"
$PidFile = Join-Path $RuntimeDir "search_opt.pid"
$LogFile = Join-Path $RuntimeDir "search_opt.log"
$ErrorLogFile = Join-Path $RuntimeDir "search_opt-error.log"
$HealthUrl = "http://127.0.0.1:$Port/api/v1/ready"
$DemoUrl = "http://127.0.0.1:$Port/demo"

Set-Location $Root
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null

function Get-ManagedProcess {
    if (-not (Test-Path $PidFile)) { return $null }
    $storedPid = (Get-Content $PidFile -Raw).Trim()
    if ($storedPid -notmatch '^\d+$') { return $null }
    return Get-Process -Id ([int]$storedPid) -ErrorAction SilentlyContinue
}

function Stop-SearchOpt {
    $process = Get-ManagedProcess
    if ($null -eq $process) {
        Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
        Write-Host "search_opt is not running."
        return
    }
    Stop-Process -Id $process.Id -Force
    $process.WaitForExit()
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    Write-Host "Stopped search_opt (PID $($process.Id))."
}

function Get-Python {
    $venvPython = Join-Path $Root ".venv\Scripts\python.exe"
    if (-not (Test-Path $venvPython)) {
        $launcher = Get-Command py -ErrorAction SilentlyContinue
        if ($null -ne $launcher) {
            Write-Host "Creating .venv with Python 3..."
            & $launcher.Source -3 -m venv (Join-Path $Root ".venv")
        } else {
            $systemPython = Get-Command python -ErrorAction SilentlyContinue
            if ($null -eq $systemPython) {
                throw "Python 3.11+ was not found. Install Python, then run .\launch.ps1 again."
            }
            Write-Host "Creating .venv..."
            & $systemPython.Source -m venv (Join-Path $Root ".venv")
        }
    }
    if (-not (Test-Path $venvPython)) { throw "The virtual environment could not be created." }
    return $venvPython
}

function Install-DependenciesIfNeeded([string]$Python) {
    & $Python -c "import fastapi, uvicorn, rapidfuzz, multipart" 2>$null
    if ($LASTEXITCODE -eq 0) { return }
    Write-Host "Installing project dependencies (first run only)..."
    & $Python -m pip install -r (Join-Path $Root "requirements.txt")
    if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }
}

function Wait-ForReady([int]$TimeoutSeconds = 90) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        try {
            $ready = Invoke-RestMethod -Uri $HealthUrl -TimeoutSec 3
            if ($ready.status -eq "ready") { return $ready }
        } catch {
            Start-Sleep -Milliseconds 750
        }
    } while ((Get-Date) -lt $deadline)
    throw "search_opt did not become ready within $TimeoutSeconds seconds. See $ErrorLogFile"
}

function Get-ListeningProcess([int]$LocalPort) {
    try {
        $connection = Get-NetTCPConnection -LocalAddress "127.0.0.1" -LocalPort $LocalPort -State Listen -ErrorAction Stop |
            Select-Object -First 1
        if ($null -ne $connection) {
            return Get-Process -Id $connection.OwningProcess -ErrorAction SilentlyContinue
        }
    } catch {
        return $null
    }
    return $null
}

function Start-OpenSearch {
    $docker = Get-Command docker -ErrorAction SilentlyContinue
    if ($null -eq $docker) { throw "Docker is required for -Backend opensearch. Use the default in-memory backend for the demo." }
    & $docker.Source compose up -d opensearch
    if ($LASTEXITCODE -ne 0) { throw "OpenSearch could not be started." }
    $deadline = (Get-Date).AddSeconds(90)
    do {
        try {
            Invoke-RestMethod -Uri "http://127.0.0.1:9200" -TimeoutSec 3 | Out-Null
            return
        } catch {
            Start-Sleep -Seconds 2
        }
    } while ((Get-Date) -lt $deadline)
    throw "OpenSearch did not become healthy within 90 seconds."
}

function Set-DemoEnvironment {
    $env:HOST = "127.0.0.1"
    $env:PORT = [string]$Port
    $env:SEARCH_BACKEND = $Backend
    $env:AUTH_ENABLED = "false"
    $env:RATE_LIMIT_ENABLED = "true"
    $env:STT_PROVIDER = "mock"
    $env:VOICE_MOCK_ENABLED = "true"
    $env:SEMANTIC_MODEL_ALLOW_DOWNLOAD = "false"
    $env:BOOTSTRAP_SAMPLE_DATA = "true"
    $env:ANALYTICS_ENABLED = "true"
}

if ($Action -eq "stop") { Stop-SearchOpt; exit 0 }

if ($Action -eq "status") {
    $process = Get-ManagedProcess
    if ($null -eq $process) { Write-Host "search_opt is stopped."; exit 1 }
    try {
        $health = Invoke-RestMethod -Uri $HealthUrl -TimeoutSec 3
        Write-Host "search_opt is running (PID $($process.Id)); readiness: $($health.status)"
        Write-Host "Demo: $DemoUrl"
        exit 0
    } catch {
        Write-Host "search_opt process $($process.Id) exists but the health endpoint is unavailable."
        exit 1
    }
}

if ($Action -eq "restart") { Stop-SearchOpt }

$Python = Get-Python
Install-DependenciesIfNeeded $Python

if ($Action -eq "validate") {
    Write-Host "Running automated tests..."
    & $Python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "Tests failed." }
    Write-Host "Running the retrieval benchmark..."
    & $Python (Join-Path $Root "scripts\run_benchmark.py")
    if ($LASTEXITCODE -ne 0) { throw "Benchmark failed." }
    Write-Host "Validation complete. Report: artifacts\benchmark_report.json"
    exit 0
}

$existing = Get-ManagedProcess
if ($null -ne $existing) {
    Write-Host "search_opt is already running (PID $($existing.Id))."
    Write-Host "Demo: $DemoUrl"
    exit 0
}

if ($Backend -eq "opensearch") { Start-OpenSearch }
Set-DemoEnvironment

$arguments = @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", [string]$Port)
if ($Foreground) {
    Write-Host "Starting search_opt in the foreground at $DemoUrl (Ctrl+C to stop)..."
    & $Python @arguments
    exit $LASTEXITCODE
}

Remove-Item $LogFile, $ErrorLogFile -Force -ErrorAction SilentlyContinue
$process = Start-Process -FilePath $Python -ArgumentList $arguments -WorkingDirectory $Root -RedirectStandardOutput $LogFile -RedirectStandardError $ErrorLogFile -WindowStyle Hidden -PassThru
Set-Content -Path $PidFile -Value $process.Id

try {
    $health = Wait-ForReady
} catch {
    if (-not $process.HasExited) { Stop-Process -Id $process.Id -Force }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    Write-Host "Startup failed. Recent error output:"
    if (Test-Path $ErrorLogFile) { Get-Content $ErrorLogFile -Tail 30 }
    throw
}

# On Windows, a venv launcher can hand execution to the base Python process.
# Record the process that actually owns the HTTP listener, not the short-lived shim.
$listenerProcess = Get-ListeningProcess $Port
if ($null -ne $listenerProcess) {
    $process = $listenerProcess
    Set-Content -Path $PidFile -Value $process.Id
}

Write-Host "search_opt is ready in the background (PID $($process.Id))."
Write-Host "Demo:    $DemoUrl"
Write-Host "API docs: http://127.0.0.1:$Port/docs"
Write-Host "Health:  $HealthUrl"
Write-Host "Logs:    $LogFile"
Write-Host "Stop:    .\launch.ps1 stop"

if (-not $NoBrowser) { Start-Process $DemoUrl }
