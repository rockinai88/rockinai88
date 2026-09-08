param(
    [switch]$RequireClean,
    [switch]$SkipRender
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $Root

function Invoke-GateStep {
    param([string]$Name, [scriptblock]$Action)
    Write-Output "GATE_START $Name"
    $global:LASTEXITCODE = 0
    & $Action
    $Code = $LASTEXITCODE
    if ($Code -ne 0) { throw "GATE_FAIL ${Name} exit=$Code" }
    Write-Output "GATE_PASS $Name"
}

$Python = (Get-Command python -ErrorAction Stop).Source
$env:PYTHONDONTWRITEBYTECODE = '1'
Invoke-GateStep 'PY_COMPILE' { & $Python -m py_compile 'scripts/generate_profile.py' 'scripts/validate-profile.py' }
if (Test-Path 'scripts/__pycache__') { Remove-Item -LiteralPath 'scripts/__pycache__' -Recurse -Force }
Invoke-GateStep 'GENERATOR_CHECK' { & $Python 'scripts/generate_profile.py' --check }
Invoke-GateStep 'PROFILE_VALIDATE' { & $Python 'scripts/validate-profile.py' }
Invoke-GateStep 'GIT_DIFF_CHECK' { git diff --check }

if ($RequireClean) {
    $Dirty = git status --porcelain
    if ($Dirty) { throw 'GATE_FAIL WORKTREE_NOT_CLEAN' }
    Write-Output 'GATE_PASS WORKTREE_CLEAN'
}

if (-not $SkipRender) {
    $EdgeCandidates = New-Object System.Collections.Generic.List[string]
    $EdgeCommand = Get-Command msedge.exe -ErrorAction SilentlyContinue
    if ($EdgeCommand) { $EdgeCandidates.Add($EdgeCommand.Source) }

    $Bases = @(${env:ProgramFiles(x86)}, $env:ProgramFiles, $env:LOCALAPPDATA) |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    foreach ($Base in $Bases) {
        $Candidate = Join-Path $Base 'Microsoft\Edge\Application\msedge.exe'
        if (Test-Path $Candidate) { $EdgeCandidates.Add($Candidate) }
    }
    foreach ($Candidate in @(
        'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
        'C:\Program Files\Microsoft\Edge\Application\msedge.exe'
    )) {
        if (Test-Path $Candidate) { $EdgeCandidates.Add($Candidate) }
    }

    $Edge = $EdgeCandidates | Select-Object -Unique | Select-Object -First 1
    if (-not $Edge) { throw 'GATE_FAIL EDGE_NOT_FOUND' }

    $Config = Get-Content -LiteralPath 'profile/profile.json' -Raw -Encoding UTF8 | ConvertFrom-Json
    $Targets = @(
        $Config.assets.hero_dark,
        $Config.assets.hero_light,
        $Config.assets.achievements_dark,
        $Config.assets.achievements_light
    )
    $Temp = Join-Path ([IO.Path]::GetTempPath()) ('rockin-profile-gate-' + [guid]::NewGuid().ToString('N'))
    $EdgeProfile = Join-Path $Temp 'edge-profile'
    New-Item -ItemType Directory -Force -Path $EdgeProfile | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $EdgeProfile 'Crashpad') | Out-Null

    try {
        foreach ($Relative in $Targets) {
            $CleanRelative = $Relative -replace '^\./', ''
            $Source = (Resolve-Path (Join-Path $Root $CleanRelative)).Path
            $Name = [IO.Path]::GetFileNameWithoutExtension($Source)
            $Shot = Join-Path $Temp ($Name + '.png')
            $Uri = ([System.Uri]::new($Source)).AbsoluteUri
            $Args = @(
                '--headless=new', '--disable-gpu', '--hide-scrollbars',
                '--run-all-compositor-stages-before-draw',
                "--user-data-dir=$EdgeProfile", '--window-size=980,620',
                "--screenshot=$Shot", $Uri
            )
            $Process = Start-Process -FilePath $Edge -ArgumentList $Args -Wait -PassThru
            if ($Process.ExitCode -ne 0) { throw "GATE_FAIL RENDER_EXIT:${Name}:$($Process.ExitCode)" }
            if (-not (Test-Path $Shot)) { throw "GATE_FAIL RENDER_MISSING:${Name}" }
            $Bytes = (Get-Item $Shot).Length
            if ($Bytes -lt 10000) { throw "GATE_FAIL RENDER_TOO_SMALL:${Name}:$Bytes" }
            Write-Output "GATE_PASS RENDER $Name bytes=$Bytes"
        }
    }
    finally {
        if (Test-Path $Temp) { Remove-Item -LiteralPath $Temp -Recurse -Force -ErrorAction SilentlyContinue }
    }
}

$Head = git rev-parse HEAD
$Branch = git branch --show-current
Write-Output "PROFILE_FULL_GATE_PASS branch=$Branch head=$Head"
