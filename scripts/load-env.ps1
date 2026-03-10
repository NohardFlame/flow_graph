# Load environment variables from .env into the current process.
# Usage (from repo root): . .\scripts\load-env.ps1
# Or: . .\scripts\load-env.ps1 -Path .env
# After loading, run: uvicorn app.api.main:app --host 0.0.0.0 --port 8000
# and in another terminal (after loading env again): python -m arq app.workers.arq_tasks.WorkerSettings

param(
    [string] $Path = ".env"
)

$envFile = $Path
if (-not [System.IO.Path]::IsPathRooted($Path)) {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $repoRoot = Split-Path -Parent $scriptDir
    $envFile = Join-Path $repoRoot $Path
}

if (-not (Test-Path -LiteralPath $envFile)) {
    Write-Warning "Env file not found: $envFile"
    if ($Path -eq ".env") {
        Write-Host "Copy .env.example to .env and fill in your values, then run this script again."
    }
    return
}

Get-Content -LiteralPath $envFile -Encoding UTF8 | ForEach-Object {
    $line = $_.Trim()
    if ($line -eq "" -or $line.StartsWith("#")) { return }
    if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') {
        $key = $matches[1]
        $val = $matches[2].Trim()
        if ($val.Length -ge 2 -and (($val.StartsWith('"') -and $val.EndsWith('"')) -or ($val.StartsWith("'") -and $val.EndsWith("'")))) {
            $val = $val.Substring(1, $val.Length - 2)
        }
        Set-Item -Path "Env:$key" -Value $val
    }
}

Write-Host "Loaded env from $envFile"
