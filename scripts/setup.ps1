param(
    [ValidateSet('cuda', 'cpu')][string]$Profile = 'cuda',
    [switch]$SkipModels
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$venvRoot = Join-Path $projectRoot '.venv'
$pythonExe = Join-Path $venvRoot 'Scripts\python.exe'
$tempRoot = Join-Path $projectRoot 'work\tmp'
New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null
$env:TEMP = $tempRoot
$env:TMP = $tempRoot
$env:PIP_CACHE_DIR = Join-Path $projectRoot 'work\pip-cache'
if (-not (Test-Path -LiteralPath $pythonExe)) {
    python -m venv --without-pip $venvRoot
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar ambiente Python 3.12.' }
}
& $pythonExe -c "import sys; assert sys.version_info[:2] == (3,12), 'Use Python 3.12 x64'"
if ($LASTEXITCODE -ne 0) { throw 'Versão Python não suportada pelo perfil de wheels.' }
# --python também prepara pip em venv sem ensurepip; TEMP fica no projeto.
python -m pip --python $pythonExe install --only-binary=:all: pip==25.2
if ($LASTEXITCODE -ne 0) { throw 'Falha ao preparar pip.' }
$torchIndex = if ($Profile -eq 'cuda') { 'https://download.pytorch.org/whl/cu124' } else { 'https://download.pytorch.org/whl/cpu' }
& $pythonExe -m pip install --only-binary=:all: torch==2.6.0 --index-url $torchIndex
if ($LASTEXITCODE -ne 0) { throw 'Wheel PyTorch indisponível; não compilar nem trocar perfil automaticamente.' }
$llamaVersion = if ($Profile -eq 'cuda') { '0.3.4' } else { '0.3.19' }
$llamaIndex = if ($Profile -eq 'cuda') { 'https://abetlen.github.io/llama-cpp-python/whl/cu124' } else { 'https://abetlen.github.io/llama-cpp-python/whl/cpu' }
& $pythonExe -m pip install --only-binary=:all: "llama-cpp-python==$llamaVersion" --extra-index-url $llamaIndex
if ($LASTEXITCODE -ne 0) { throw 'Wheel llama.cpp indisponível; instalação interrompida sem compilação C++.' }
& $pythonExe -m pip install --only-binary=:all: -r (Join-Path $projectRoot 'requirements-models.txt') pytest==8.4.2
if ($LASTEXITCODE -ne 0) { throw 'Falha nas dependências.' }
& $pythonExe -m pip install --no-deps -e $projectRoot
if ($LASTEXITCODE -ne 0) { throw 'Falha ao registrar CLI.' }
Set-Content -LiteralPath (Join-Path $venvRoot 'rag-profile.txt') -Value $Profile
& $pythonExe (Join-Path $projectRoot 'main.py') --profile $Profile --diagnose
if ($LASTEXITCODE -ne 0) { throw 'Diagnóstico de backend falhou; verifique driver ou selecione CPU.' }
if (-not $SkipModels) {
    & $pythonExe (Join-Path $projectRoot 'main.py') --profile $Profile --prepare
    if ($LASTEXITCODE -ne 0) { throw 'Falha no download dos modelos; repita --prepare.' }
}
Write-Host "Preparação concluída ($Profile). Execute: $pythonExe $projectRoot\main.py --profile $Profile"
