# WinUx shortcut helper (Python can't edit .lnk files by itself).
#   -Mode list  -Out file.json            : list shortcuts in the usual places
#   -Mode set   -In file.json [-Out log]  : set icons  [{path, icon}]  (icon "" = app's own icon)
#   -Mode admin -In file.json  -Out log   : same as set, plus the folder icon; run elevated
param([string]$Mode, [string]$In, [string]$Out)

$ErrorActionPreference = "Continue"
$ws = New-Object -ComObject WScript.Shell

function Set-Icon($path, $icon) {
    if ($path -like "*.url") {
        # internet shortcuts (Steam games) keep their icon as text lines
        $new = New-Object System.Collections.Generic.List[string]
        $added = $false
        foreach ($line in Get-Content -LiteralPath $path) {
            if ($line -match "^(IconFile|IconIndex)=") { continue }
            $new.Add($line)
            if ($icon -and -not $added -and $line -match "^\[InternetShortcut\]") {
                $new.Add("IconFile=$icon"); $new.Add("IconIndex=0"); $added = $true
            }
        }
        if ($icon -and -not $added) { $new.Add("[InternetShortcut]"); $new.Add("IconFile=$icon"); $new.Add("IconIndex=0") }
        Set-Content -LiteralPath $path -Value $new -Encoding ASCII
    } else {
        $s = $ws.CreateShortcut($path)
        # "file.ico" gets ",0" added; "file.exe,3" (an original icon WinUx saved) is used as-is
        if (-not $icon -or $icon -eq ",0") { $s.IconLocation = ",0" }
        elseif ($icon -match ",-?\d+$") { $s.IconLocation = $icon }
        else { $s.IconLocation = "$icon,0" }
        $s.Save()
    }
    # touch it so Explorer notices
    (Get-Item -LiteralPath $path).LastWriteTime = Get-Date
}

if ($Mode -eq "list") {
    $places = [ordered]@{
        "desktop"        = [Environment]::GetFolderPath("Desktop")
        "public-desktop" = "$env:PUBLIC\Desktop"
        "start"          = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs"
        "public-start"   = "$env:ProgramData\Microsoft\Windows\Start Menu\Programs"
        "taskbar"        = "$env:APPDATA\Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar"
    }
    $items = New-Object System.Collections.Generic.List[object]
    foreach ($k in $places.Keys) {
        $p = $places[$k]
        if (-not (Test-Path -LiteralPath $p)) { continue }
        # desktops and the taskbar: only what's directly there (Start menu has sub-folders)
        if ($k -like "*start") { $files = Get-ChildItem -LiteralPath $p -Recurse -File -ErrorAction SilentlyContinue }
        else { $files = Get-ChildItem -LiteralPath $p -File -ErrorAction SilentlyContinue }
        $files | Where-Object { $_.Extension -in ".lnk", ".url" } | ForEach-Object {
            $f = $_.FullName
            $item = @{ path = $f; place = $k; name = $_.BaseName; target = ""; args = ""; icon = ""; url = "" }
            try {
                if ($_.Extension -eq ".lnk") {
                    $s = $ws.CreateShortcut($f)
                    $item.target = $s.TargetPath; $item.args = $s.Arguments; $item.icon = $s.IconLocation
                } else {
                    foreach ($line in Get-Content -LiteralPath $f) {
                        if ($line -match "^URL=(.*)") { $item.url = $Matches[1] }
                        if ($line -match "^IconFile=(.*)") { $item.icon = $Matches[1] }
                    }
                }
            } catch {}
            $items.Add($item)
        }
    }
    ConvertTo-Json -InputObject @($items.ToArray()) -Depth 3 | Set-Content -LiteralPath $Out -Encoding UTF8
    exit 0
}

$log = @()
$jobs = Get-Content -LiteralPath $In -Raw | ConvertFrom-Json
foreach ($j in @($jobs.shortcuts)) {
    try { Set-Icon $j.path $j.icon; $log += "ok $($j.path)" } catch { $log += "fail $($j.path): $_" }
}
if ($Mode -eq "admin" -and $jobs.folder -ne $null) {
    # the yellow folder icon everywhere (needs admin)
    $key = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Icons"
    try {
        if ($jobs.folder) {
            if (-not (Test-Path $key)) { New-Item -Path $key -Force | Out-Null }
            Set-ItemProperty -Path $key -Name "3" -Value "$($jobs.folder),0"
            Set-ItemProperty -Path $key -Name "4" -Value "$($jobs.folder),0"
        } elseif (Test-Path $key) {
            Remove-ItemProperty -Path $key -Name "3", "4" -ErrorAction SilentlyContinue
        }
        $log += "ok folder"
    } catch { $log += "fail folder: $_" }
}
if ($Mode -eq "admin" -and @($jobs.styler).Count -gt 0) {
    # Windhawk's Taskbar Styler: the Start button and search icons (needs admin)
    try {
        $base = "SOFTWARE\Windhawk\Engine\Mods\windows-11-taskbar-styler"
        $rk = [Microsoft.Win32.Registry]::LocalMachine.CreateSubKey("$base\Settings")
        foreach ($e in @($jobs.styler)) {
            $rk.SetValue("controlStyles[$($e.index)].target", [string]$e.target)
            $n = 0
            foreach ($st in @($e.styles)) { $rk.SetValue("controlStyles[$($e.index)].styles[$n]", [string]$st); $n++ }
            $rk.SetValue("controlStyles[$($e.index)].styles[$n]", "")
        }
        $rk.Close()
        # tell Windhawk the settings changed so the mod reloads them
        $mk = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey($base, $true)
        $mk.SetValue("SettingsChangeTime", [int][DateTimeOffset]::UtcNow.ToUnixTimeSeconds(), [Microsoft.Win32.RegistryValueKind]::DWord)
        $mk.Close()
        $log += "ok styler"
    } catch { $log += "fail styler: $_" }
}
if ($Out) { $log | Set-Content -LiteralPath $Out -Encoding UTF8 }
