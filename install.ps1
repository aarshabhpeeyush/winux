# WinUx installer. Works on Windows 10 and 11.
# Run it with install.bat (double-click). Nothing is changed without asking.

$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $Here

# Everything this installer does is also saved to install-log.txt (send it if something breaks).
try { Start-Transcript -LiteralPath (Join-Path $Here "install-log.txt") -Force | Out-Null } catch {}

# If anything goes wrong, say what and where the log is, instead of just closing.
trap {
    Write-Host ""
    Write-Host "  * Something went wrong: $_" -ForegroundColor Red
    Write-Host "  * Please send install-log.txt (in the WinUx folder) to the WinUx GitHub page." -ForegroundColor Red
    try { Stop-Transcript | Out-Null } catch {}
    exit 1
}

# Files downloaded from the internet are "blocked" by Windows, which can stop scripts. Unblock ours.
Get-ChildItem -LiteralPath $Here -Recurse -File -ErrorAction SilentlyContinue | Unblock-File -ErrorAction SilentlyContinue

function Say($text, $color = "White") { Write-Host $text -ForegroundColor $color }
function Ask($question) {
    $a = Read-Host "$question [Y/n]"
    return ($a -eq "" -or $a -match "^[Yy]")
}
function Have-Winget { return [bool](Get-Command winget -ErrorAction SilentlyContinue) }
function Winget-Install($id, $extra = @()) {
    $wargs = @("install", "-e", "--id", $id, "--accept-package-agreements", "--accept-source-agreements") + $extra
    & winget @wargs
    return ($LASTEXITCODE -eq 0 -or $LASTEXITCODE -eq -1978335189)   # 0 = installed, -1978335189 = already installed
}

Say ""
Say "  * WinUx installer" Yellow
Say "  * Windows customization, Deltarune style." Yellow
Say ""

$build = [Environment]::OSVersion.Version.Build
if ($build -lt 17763) {
    Say "  * WinUx needs Windows 10 (version 1809 or newer) or Windows 11." Red
    exit 1
}
Say ("  * Found Windows " + ($(if ($build -ge 22000) { "11" } else { "10" })) + " (build $build).")

# ------------------------------------------------------------ Python
function Find-Pythonw {
    $found = @()
    # the py launcher knows every real Python install
    if (Get-Command py -ErrorAction SilentlyContinue) {
        try {
            $exe = & py -3 -c "import sys; print(sys.base_prefix)" 2>$null
            if ($exe) { $found += (Join-Path $exe.Trim() "pythonw.exe") }
        } catch {}
    }
    $found += Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\Python3*\pythonw.exe" -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | ForEach-Object FullName
    $found += Get-ChildItem "$env:ProgramFiles\Python3*\pythonw.exe" -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | ForEach-Object FullName
    foreach ($p in $found) {
        if (-not (Test-Path $p)) { continue }
        $python = Join-Path (Split-Path $p) "python.exe"
        try {
            $ok = & $python -c "import sys; print(sys.version_info >= (3, 10))" 2>$null
            if ($ok -and $ok.Trim() -eq "True") { return $p }
        } catch {}
    }
    return $null
}

$pyw = Find-Pythonw
if (-not $pyw) {
    Say "  * WinUx runs on Python 3.10 or newer, and it isn't installed." Yellow
    if ((Have-Winget) -and (Ask "  Install Python 3.12 now (free, from python.org)?")) {
        Winget-Install "Python.Python.3.12" @("--scope", "user") | Out-Null
        $pyw = Find-Pythonw
    }
    if (-not $pyw) {
        Say "  * Please install Python from https://www.python.org/downloads/ and run this again." Red
        exit 1
    }
}
Say "  * Python: $pyw" Green
# Start WinUx.bat reads this so it always uses the right Python
Set-Content -LiteralPath (Join-Path $Here ".pythonw") -Value $pyw -Encoding ASCII

# ------------------------------------------------------------ helper apps
Say ""
Say "  * WinUx is a hub: it drives these free apps. Pick the ones you want."
Say "    (You can skip any of them. WinUx just hides what's missing.)"
Say ""

if (-not (Have-Winget)) {
    Say "  * winget (App Installer) isn't on this PC, so I can't install the apps for you." Yellow
    Say "    Get App Installer from the Microsoft Store, or install the apps yourself:"
    Say "      Lively Wallpaper  https://www.rocksdanister.com/lively/"
    Say "      TranslucentTB     https://apps.microsoft.com/detail/9pf4kz2vn4w9"
    Say "      Rainmeter         https://www.rainmeter.net/"
    Say "      Windhawk          https://windhawk.net/"
} else {
    $apps = @(
        @{ name = "Lively Wallpaper"; why = "live wallpapers (needed for every WinUx theme's animated background)"; id = "rocksdanister.LivelyWallpaper" },
        @{ name = "TranslucentTB";    why = "see-through and colored taskbar";                                       id = "9PF4KZ2VN4W9"; extra = @("--source", "msstore") },
        @{ name = "Rainmeter";        why = "desktop widgets (clock, music, text box)";                              id = "Rainmeter.Rainmeter" },
        @{ name = "Windhawk";         why = "the mod shop (new taskbar and Start menu styles)";                      id = "RamenSoftware.Windhawk" }
    )
    foreach ($app in $apps) {
        if (Ask ("  Install " + $app.name + " - " + $app.why + "?")) {
            $extra = if ($app.extra) { $app.extra } else { @() }
            if (Winget-Install $app.id $extra) { Say ("  * " + $app.name + " is ready.") Green }
            else { Say ("  * " + $app.name + " didn't install. You can try again later.") Yellow }
        }
    }

    # Lively's web wallpapers run on WebView2. Windows 11 has it; some Windows 10 PCs don't.
    $wv = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
    $hasWv = @("HKLM:\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\$wv",
               "HKLM:\SOFTWARE\Microsoft\EdgeUpdate\Clients\$wv",
               "HKCU:\SOFTWARE\Microsoft\EdgeUpdate\Clients\$wv") |
             Where-Object { (Get-ItemProperty $_ -Name pv -ErrorAction SilentlyContinue).pv -and (Get-ItemProperty $_).pv -ne "0.0.0.0" }
    if (-not $hasWv) {
        Say "  * WinUx's live wallpapers need Microsoft's WebView2 Runtime, and it's missing." Yellow
        if (Ask "  Install WebView2 Runtime (free, from Microsoft)?") {
            Winget-Install "Microsoft.EdgeWebView2Runtime" | Out-Null
        }
    }
}

# ------------------------------------------------------------ start with Windows
Say ""
$server = Join-Path $Here "server.py"
if (Ask "  Start WinUx automatically when you turn on your PC?") {
    $cmd = "`"$pyw`" `"$server`" --no-browser"
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "WinUx" -Value $cmd
    Say "  * WinUx will start with Windows. (Switch it off any time in BACKUP.)" Green
}

# ------------------------------------------------------------ go
Say ""
Say "  * All done! Opening WinUx..." Yellow
Say "  * Your current look is backed up the first time WinUx starts."
Say "    BACKUP > RESTORE puts everything back exactly how it was."
Start-Process -FilePath (Join-Path $Here "Start WinUx.bat") -WorkingDirectory $Here
try { Stop-Transcript | Out-Null } catch {}
