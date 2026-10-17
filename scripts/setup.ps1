param(
    [ValidateSet('mixed', 'cuda', 'cpu')][string]$Profile = 'mixed',
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
$env:PYTHONUTF8 = '1'
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
$usesCuda = $Profile -ne 'cpu'
$torchIndex = if ($usesCuda) { 'https://download.pytorch.org/whl/cu124' } else { 'https://download.pytorch.org/whl/cpu' }
$torchVersion = if ($usesCuda) { '2.6.0+cu124' } else { '2.6.0+cpu' }
$cachedTorch = Join-Path $projectRoot 'work\wheels\torch-2.6.0+cu124-cp312-cp312-win_amd64.whl'
if ($usesCuda -and (Test-Path -LiteralPath $cachedTorch)) {
    & $pythonExe -m pip install --only-binary=:all: $cachedTorch
} else {
    & $pythonExe -m pip install --only-binary=:all: "torch==$torchVersion" --index-url $torchIndex
}
if ($LASTEXITCODE -ne 0) { throw 'Wheel PyTorch indisponível; não compilar nem trocar perfil automaticamente.' }
$llamaVersion = if ($usesCuda) { '0.3.36' } else { '0.3.19' }
$llamaIndex = if ($usesCuda) { 'https://abetlen.github.io/llama-cpp-python/whl/cu124' } else { 'https://abetlen.github.io/llama-cpp-python/whl/cpu' }
if ($usesCuda) {
    # Modern upstream CUDA wheels use py3-none, not cp312. Pin backend and asset digest.
    $llamaWheel = 'https://github.com/abetlen/llama-cpp-python/releases/download/v0.3.36-cu124/llama_cpp_python-0.3.36-py3-none-win_amd64.whl#sha256=7086b98420cf9cca5e3f14181edc4332038bfb0a0e380370a693806bb527911f'
    $cachedLlama = Join-Path $projectRoot 'work\wheels\llama_cpp_python-0.3.36-py3-none-win_amd64.whl'
    if (Test-Path -LiteralPath $cachedLlama) {
        if ((Get-FileHash -LiteralPath $cachedLlama -Algorithm SHA256).Hash.ToLowerInvariant() -ne '7086b98420cf9cca5e3f14181edc4332038bfb0a0e380370a693806bb527911f') {
            throw 'Wheel CUDA local com SHA256 incompatível.'
        }
        & $pythonExe -m pip install --only-binary=:all: $cachedLlama
    } else {
        & $pythonExe -m pip install --only-binary=:all: $llamaWheel
    }
} else {
    & $pythonExe -m pip install --only-binary=:all: "llama-cpp-python==$llamaVersion" --extra-index-url $llamaIndex
}
if ($LASTEXITCODE -ne 0) { throw 'Wheel llama.cpp indisponível; instalação interrompida sem compilação C++.' }
& $pythonExe -m pip install --only-binary=:all: -r (Join-Path $projectRoot 'requirements-models.txt') -c (Join-Path $projectRoot 'requirements-lock.txt') pytest==8.4.2
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
