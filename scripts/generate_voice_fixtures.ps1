$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Speech
$outputDir = Join-Path $PSScriptRoot "..\\sample_data\\voice"
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer

$fixtures = @(
  @{ filename = "english_pph_assessment.wav"; text = "postpartum hemorrhage assessment" ; expected_group_id = "postpartum-hemorrhage"; preferred_language = "English" },
  @{ filename = "code_mixed_lam.wav"; text = "family planning LAM hindi" ; expected_group_id = "family-planning-lam"; preferred_language = "Hindi" },
  @{ filename = "romanized_kmc.wav"; text = "K M C ki samajh" ; expected_group_id = "kangaroo-mother-care"; preferred_language = "Hindi" }
)

$manifest = @()
foreach ($fixture in $fixtures) {
  $path = Join-Path $outputDir $fixture.filename
  $synth.SetOutputToWaveFile($path)
  $synth.Speak($fixture.text)
  $synth.SetOutputToDefaultAudioDevice()
  $manifest += @{
    path = "sample_data/voice/$($fixture.filename)"
    expected_group_id = $fixture.expected_group_id
    preferred_language = $fixture.preferred_language
  }
}

$manifestPath = Join-Path $outputDir "manifest.json"
$manifest | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 $manifestPath
Write-Host "Voice fixtures written to $outputDir"
