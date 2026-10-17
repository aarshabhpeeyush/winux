# WinUx lock screen helper (Windows' own LockScreen API, no admin needed).
#   -Image picture.png         : set the lock screen picture
#   -SaveOriginal backup.jpg   : save a copy of the current lock screen picture first
#   -Out log.txt               : what happened
param([string]$Image, [string]$SaveOriginal, [string]$Out)

$log = @()
try {
    Add-Type -AssemblyName System.Runtime.WindowsRuntime
    $methods = [System.WindowsRuntimeSystemExtensions].GetMethods()
    $asTaskOp = $methods | Where-Object { $_.Name -eq "AsTask" -and $_.GetParameters().Count -eq 1 -and
                                          $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' } | Select-Object -First 1
    $asTaskAction = $methods | Where-Object { $_.Name -eq "AsTask" -and $_.GetParameters().Count -eq 1 -and
                                              $_.GetParameters()[0].ParameterType.Name -eq "IAsyncAction" } | Select-Object -First 1
    function Await($op, [Type]$type) {
        $task = $asTaskOp.MakeGenericMethod($type).Invoke($null, @($op))
        $task.Wait(-1) | Out-Null
        $task.Result
    }
    function AwaitAction($op) { $task = $asTaskAction.Invoke($null, @($op)); $task.Wait(-1) | Out-Null }

    [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime] | Out-Null
    [Windows.System.UserProfile.LockScreen, Windows.System.UserProfile, ContentType = WindowsRuntime] | Out-Null

    if ($SaveOriginal -and -not (Test-Path -LiteralPath $SaveOriginal)) {
        try {
            # the picture Windows is showing now, so Restore can put it back
            $stream = [Windows.System.UserProfile.LockScreen]::GetImageStream()
            if ($stream) {
                # read it with a DataReader (works with Windows' own stream objects)
                [Windows.Storage.Streams.DataReader, Windows.Storage.Streams, ContentType = WindowsRuntime] | Out-Null
                $reader = [Windows.Storage.Streams.DataReader]::new($stream.GetInputStreamAt(0))
                $n = Await ($reader.LoadAsync([uint32]$stream.Size)) ([uint32])
                $bytes = New-Object byte[] $n
                $reader.ReadBytes($bytes)
                [System.IO.File]::WriteAllBytes($SaveOriginal, $bytes)
                $log += "ok saved original"
            }
        } catch {
            # fall back to the file Windows keeps for it
            try {
                $uri = [Windows.System.UserProfile.LockScreen]::OriginalImageFile
                if ($uri -and $uri.IsFile -and (Test-Path -LiteralPath $uri.LocalPath)) {
                    Copy-Item -LiteralPath $uri.LocalPath -Destination $SaveOriginal
                    $log += "ok saved original (file)"
                } else { $log += "skip original: $_" }
            } catch { $log += "skip original: $_" }
        }
    }
    if ($Image) {
        $file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($Image)) ([Windows.Storage.StorageFile])
        AwaitAction ([Windows.System.UserProfile.LockScreen]::SetImageFileAsync($file))
        $log += "ok set $Image"
    }
} catch {
    $log += "fail $_"
}
if ($Out) { $log | Set-Content -LiteralPath $Out -Encoding UTF8 }
