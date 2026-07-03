# Build script for transfer_sd executable using PyInstaller
# Run from project root in PowerShell

$exeName = "transfer_sd"
$entry = "transfer_sd.py"
$config = "config.json"

if (-not (Test-Path $entry)) {
    Write-Error "Entry file $entry not found. Run this from project root."
    exit 1
}

if (-not (Test-Path $config)) {
    Write-Warning "No config.json found in project root. PyInstaller will still build, but you should provide a config next to the exe."
}


# Ensure pyinstaller is available (use python -m PyInstaller to avoid PATH issues)
try {
    python -m PyInstaller --version | Out-Null
} catch {
    Write-Host "PyInstaller not found. Installing into current environment..."
    pip install pyinstaller
}

# Build onefile exe and include config.json as data so it is available at runtime
$addData = "config.json;."
python -m PyInstaller --onefile --name $exeName --add-data $addData $entry

Write-Host "Build finished. See dist\$exeName.exe and the bundled files in build and dist."
