param(
    [switch]$CheckOnly,
    [switch]$SkipRender
)

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $Root
$Python = (Get-Command python -ErrorAction Stop).Source
$env:PYTHONDONTWRITEBYTECODE = '1'

if ($CheckOnly) {
    & $Python 'scripts/generate_profile.py' --check
    if ($LASTEXITCODE -ne 0) { throw 'PROFILE_MAINTENANCE_GENERATOR_CHECK_FAIL' }
}
else {
    & $Python 'scripts/generate_profile.py'
    if ($LASTEXITCODE -ne 0) { throw 'PROFILE_MAINTENANCE_GENERATE_FAIL' }
}

$Gate = Join-Path $PSScriptRoot 'profile-full-gate.ps1'
& $Gate -SkipRender:$SkipRender
if ($LASTEXITCODE -ne $null -and $LASTEXITCODE -ne 0) { throw 'PROFILE_MAINTENANCE_GATE_FAIL' }
Write-Output 'PROFILE_MAINTENANCE_PASS'
