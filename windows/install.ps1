# YouTube downloader - Windows one-click installer
# Installs uv / deno / ffmpeg (user-local, no admin rights), syncs Python deps,
# and creates a desktop shortcut that starts the local web UI.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot   # project root ( parent of windows\ )

Write-Host "==> Project root: $root"

# --- 1. uv (Python runtime & dependency manager) -----------------------------
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "==> Installing uv..."
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
}
$env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
uv --version

# --- 2. deno (JS runtime required by yt-dlp for full format extraction) ------
if (-not (Get-Command deno -ErrorAction SilentlyContinue)) {
    Write-Host "==> Installing deno..."
    Invoke-RestMethod https://deno.land/install.ps1 | Invoke-Expression
}
$env:Path = "$env:USERPROFILE\.deno\bin;$env:Path"

# --- 3. ffmpeg (downloaded from the official gyan.dev build at install time; -
#        not redistributed with this project - see docs/DESIGN.md 6.1) --------
$tools = Join-Path $root "tools"
if (-not (Test-Path (Join-Path $tools "ffmpeg.exe"))) {
    Write-Host "==> Downloading ffmpeg (about 80 MB)..."
    New-Item -ItemType Directory -Force -Path $tools | Out-Null
    $zip = Join-Path $env:TEMP "ffmpeg-release-essentials.zip"
    # gyan.dev가 일시 장애(503 등)일 수 있어 URL별 3회 재시도 후 미러로 폴백
    $ffmpegUrls = @(
        "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
        "https://github.com/BtbN/FFmpeg-Builds/releases/latest/download/ffmpeg-master-latest-win64-gpl.zip"
    )
    $downloaded = $false
    foreach ($url in $ffmpegUrls) {
        for ($try = 1; $try -le 3; $try++) {
            try {
                Invoke-WebRequest $url -OutFile $zip
                $downloaded = $true
                break
            } catch {
                Write-Host "  attempt $try/3 failed ($url): $($_.Exception.Message)"
                if ($try -lt 3) { Start-Sleep -Seconds (10 * $try) }
            }
        }
        if ($downloaded) { break }
        Write-Host "==> Switching to fallback mirror..."
    }
    if (-not $downloaded) {
        Write-Error "ffmpeg download failed from all mirrors"
        exit 1
    }
    $extract = Join-Path $env:TEMP "ffmpeg_extract"
    Expand-Archive $zip -DestinationPath $extract -Force
    Get-ChildItem -Path $extract -Recurse -Include ffmpeg.exe, ffprobe.exe |
        Copy-Item -Destination $tools
    Remove-Item $zip
    Remove-Item -Recurse -Force $extract
}
& (Join-Path $tools "ffmpeg.exe") -version | Select-Object -First 1

# --- 4. Python + libraries (isolated inside the project, nothing global) -----
Write-Host "==> Installing Python dependencies..."
Set-Location $root
uv sync

# --- 5. Desktop shortcut (GUI app, no console window) -------------------------
$desktop = [Environment]::GetFolderPath("Desktop")
$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut((Join-Path $desktop "YouTube Downloader.lnk"))
$sc.TargetPath = Join-Path $root ".venv\Scripts\pythonw.exe"   # pythonw = consoleless
$sc.Arguments = "gui.py"
$sc.WorkingDirectory = $root
$sc.Save()
Write-Host "==> Desktop shortcut created: YouTube Downloader (GUI)"

Write-Host ""
Write-Host "==> Install complete. Double-click 'YouTube Downloader' on your desktop."
