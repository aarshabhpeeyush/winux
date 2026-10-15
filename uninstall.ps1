# WinUx uninstaller. Removes WinUx's own bits; your apps (Lively, Rainmeter...) stay.
# Tip: first open WinUx > BACKUP > RESTORE to put your original look back.

$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
function Say($text, $color = "White") { Write-Host $text -ForegroundColor $color }

Say ""
Say "  * WinUx uninstaller" Yellow
Say "  * Did you click BACKUP > RESTORE in WinUx first? That puts your original look back." Yellow
$a = Read-Host "  Remove WinUx now? [y/N]"
if ($a -notmatch "^[Yy]") { Say "  * Nothing was changed."; exit 0 }

# stop the WinUx server (it listens on port 7777)
Get-NetTCPConnection -LocalPort 7777 -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }

# no more starting with Windows
Remove-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "WinUx" -ErrorAction SilentlyContinue

# WinUx's live wallpapers inside Lively's library
$lib = Join-Path $env:LOCALAPPDATA "Lively Wallpaper\Library\wallpapers"
Get-ChildItem $lib -Directory -Filter "winux.*" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force

# WinUx's Rainmeter widgets
$ini = Join-Path $env:APPDATA "Rainmeter\Rainmeter.ini"
if (Test-Path $ini) {
    $skins = (Get-Content $ini -Encoding Unicode | Where-Object { $_ -like "SkinPath=*" }) -replace "^SkinPath=", ""
    if (-not $skins) { $skins = Join-Path ([Environment]::GetFolderPath("MyDocuments")) "Rainmeter\Skins" }
    if ($skins) {
        $rm = Join-Path $env:ProgramFiles "Rainmeter\Rainmeter.exe"
        if (Test-Path $rm) { & $rm "!DeactivateGroup" "WinUx" }
        Start-Sleep -Seconds 1
        Remove-Item (Join-Path $skins "WinUx") -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Say ""
Say "  * WinUx is removed from Windows." Green
Say "  * You can now delete this folder: $Here"
Say "  * Lively, TranslucentTB, Rainmeter and Windhawk are still installed. Remove them in"
Say "    Settings > Apps if you don't want them."
