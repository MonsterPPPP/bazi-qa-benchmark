$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $repoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) {
    uv venv (Join-Path $repoRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
}
uv pip install --python $pythonExe -r (Join-Path $repoRoot 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
& $pythonExe (Join-Path $PSScriptRoot 'prepare_site.py')
if ($LASTEXITCODE -ne 0) { throw 'Recovered-data verification failed.' }
& $pythonExe (Join-Path $repoRoot 'tools\benchmark-pages\scripts\build_site.py') --source (Join-Path $repoRoot 'docs') --out (Join-Path $repoRoot '_site') --strict
if ($LASTEXITCODE -ne 0) { throw 'Site build failed.' }
Write-Output "Built site: $(Join-Path $repoRoot '_site')"
