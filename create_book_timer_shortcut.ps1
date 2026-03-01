$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$launcherPath = Join-Path $repoRoot "start_book_timer.cmd"
$desktopPath = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktopPath "Book Timer.lnk"

if (-not (Test-Path $launcherPath)) {
    Write-Error "Launcher not found: $launcherPath"
    exit 1
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $launcherPath
$shortcut.WorkingDirectory = $repoRoot
$shortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,13"
$shortcut.Description = "Launch the Reading Books Timer app"
$shortcut.Save()

Write-Host "Shortcut created:" $shortcutPath
