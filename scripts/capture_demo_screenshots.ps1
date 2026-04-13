param(
  [string]$HostAddress = "127.0.0.1",
  [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
$chromeCandidates = @(
  "C:\Program Files\Google\Chrome\Application\chrome.exe",
  "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
  "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
  "C:\Program Files\Microsoft\Edge\Application\msedge.exe"
)
$chrome = $chromeCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not (Test-Path $python)) {
  throw "Python virtual environment was not found at $python"
}

if (-not $chrome) {
  throw "No supported Chrome/Edge binary was found."
}

$imageDir = Join-Path $root "docs\images"
$logDir = Join-Path $root "artifacts"
$browserProfileDir = Join-Path $root ".cache\browser-profile"
$stdoutLog = Join-Path $logDir "demo-server.out.log"
$stderrLog = Join-Path $logDir "demo-server.err.log"

New-Item -ItemType Directory -Force -Path $imageDir | Out-Null
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
New-Item -ItemType Directory -Force -Path $browserProfileDir | Out-Null

$env:AUTH_ENABLED = "false"
$env:RATE_LIMIT_ENABLED = "false"
$env:STT_PROVIDER = "mock"
$env:VOICE_MOCK_ENABLED = "true"
$env:ENABLE_SEMANTIC_SEARCH = "false"
$env:BOOTSTRAP_SAMPLE_DATA = "true"

$server = Start-Process `
  -FilePath $python `
  -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", $HostAddress, "--port", "$Port") `
  -WorkingDirectory $root `
  -RedirectStandardOutput $stdoutLog `
  -RedirectStandardError $stderrLog `
  -PassThru

try {
  $healthUrl = "http://$HostAddress`:$Port/api/v1/health"
  $attempts = 0
  do {
    Start-Sleep -Milliseconds 500
    $attempts += 1
    try {
      Invoke-WebRequest -UseBasicParsing -Uri $healthUrl | Out-Null
      $ready = $true
    } catch {
      $ready = $false
    }
  } while (-not $ready -and $attempts -lt 120)

  if (-not $ready) {
    throw "Local demo server did not become ready."
  }

  $captures = @(
    @{
      Url = "http://$HostAddress`:$Port/demo"
      Output = Join-Path $imageDir "demo-home.png"
      Size = "1440,1180"
    },
    @{
      Url = "http://$HostAddress`:$Port/demo?q=hindi%20kmc%20course&language=Hindi&sort=relevance&autorun=1"
      Output = Join-Path $imageDir "demo-results.png"
      Size = "1440,1400"
    },
    @{
      Url = "http://$HostAddress`:$Port/demo?q=postpartm%20hemorhage%20managment&sort=relevance&autorun=1"
      Output = Join-Path $imageDir "demo-repair.png"
      Size = "1440,1400"
    }
  )

  foreach ($capture in $captures) {
    & $chrome `
      --headless `
      --disable-gpu `
      --disable-crash-reporter `
      --disable-breakpad `
      --hide-scrollbars `
      --no-first-run `
      --no-default-browser-check `
      --user-data-dir=$browserProfileDir `
      --window-size=$($capture.Size) `
      --virtual-time-budget=6000 `
      --screenshot=$($capture.Output) `
      $capture.Url | Out-Null
  }
} finally {
  if ($server -and -not $server.HasExited) {
    Stop-Process -Id $server.Id -Force
  }
}
