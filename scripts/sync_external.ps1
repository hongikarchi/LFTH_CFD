# Sync external_data/ <-> 회사 SMB share via robocopy.
#
# 회사 SMB host는 머신마다 다를 수 있음 (DNS / IP). 환경 변수
# $env:LEAFLAB_EXTERNAL_ROOT 에 자기 머신에 맞는 UNC 경로를 설정해두고 사용.
#
# Usage:
#   .\scripts\sync_external.ps1 pull   # SMB → local mirror
#   .\scripts\sync_external.ps1 push   # local → SMB (use with care)
#
# 사전 셋업 예시:
#   [Environment]::SetEnvironmentVariable(
#     "LEAFLAB_EXTERNAL_ROOT",
#     "\\Lifethings\Lifethings_02\PROJECTS\2026 Project\2605-서부티앤디 건축물 미술작품\06_3D",
#     "User")
#   # 또는 DNS 안 풀릴 때:
#   #   "\\192.168.0.100\Lifethings_02\PROJECTS\2026 Project\..."

param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("pull", "push")]
    [string]$Direction
)

$ErrorActionPreference = "Stop"

$SmbRoot = $env:LEAFLAB_EXTERNAL_ROOT
if (-not $SmbRoot) {
    Write-Error @"
LEAFLAB_EXTERNAL_ROOT 환경 변수가 설정되어 있지 않습니다.

설정 예시 (PowerShell):
  [Environment]::SetEnvironmentVariable(
    'LEAFLAB_EXTERNAL_ROOT',
    '\\Lifethings\Lifethings_02\PROJECTS\2026 Project\2605-서부티앤디 건축물 미술작품\06_3D',
    'User')

설정 후 새 PowerShell 열고 다시 시도하세요.
"@
    exit 1
}

if (-not (Test-Path -LiteralPath $SmbRoot)) {
    Write-Warning "SMB 경로에 접근할 수 없습니다: $SmbRoot"
    Write-Warning "VPN/회사망 연결을 확인하거나 host 부분을 IP로 변경해보세요."
    Write-Warning "예: \\Lifethings\... → \\192.168.0.100\..."
    exit 2
}

$RepoRoot = Split-Path -Parent $PSScriptRoot
$LocalRoot = Join-Path $RepoRoot "external_data"
$RemoteLeafLab = Join-Path $SmbRoot "leaf-water-lab"

# robocopy flags:
#   /MIR   mirror tree (delete extra files in dest)
#   /Z     restartable mode (resume on disconnect)
#   /R:2   retry 2 times on failure
#   /W:5   wait 5s between retries
#   /MT:8  multithread
#   /XO    exclude older (don't overwrite newer)
$Flags = @("/MIR", "/Z", "/R:2", "/W:5", "/MT:8", "/XO")

if ($Direction -eq "pull") {
    Write-Host "Pulling: $RemoteLeafLab -> $LocalRoot"
    if (-not (Test-Path -LiteralPath $LocalRoot)) {
        New-Item -ItemType Directory -Path $LocalRoot | Out-Null
    }
    & robocopy $RemoteLeafLab $LocalRoot $Flags
}
else {
    Write-Host "Pushing: $LocalRoot -> $RemoteLeafLab"
    if (-not (Test-Path -LiteralPath $RemoteLeafLab)) {
        New-Item -ItemType Directory -Path $RemoteLeafLab | Out-Null
    }
    & robocopy $LocalRoot $RemoteLeafLab $Flags
}

# robocopy exit codes: 0-7 are success; 8+ are failures
if ($LASTEXITCODE -ge 8) {
    Write-Error "robocopy failed (exit code $LASTEXITCODE)"
    exit $LASTEXITCODE
}
exit 0
