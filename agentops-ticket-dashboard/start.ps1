param([string]$Repo,[int]$Port=8765)
if ([string]::IsNullOrWhiteSpace($Repo)) {
    $Repo = (Get-Location).Path
}
$ScriptPath = Join-Path $PSScriptRoot 'server.py'
python $ScriptPath --repo $Repo --port $Port
