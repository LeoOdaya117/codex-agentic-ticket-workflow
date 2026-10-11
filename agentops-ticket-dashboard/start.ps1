param([string[]]$Repo,[int]$Port=8765)
if (-not $Repo -or $Repo.Count -eq 0) {
    $Repo = @((Get-Location).Path)
}
$ScriptPath = Join-Path $PSScriptRoot 'server.py'
$Arguments = @()
foreach ($RepoPathItem in $Repo) {
    $Arguments += @('--repo', $RepoPathItem)
}
$Arguments += @('--port', $Port)
python $ScriptPath @Arguments
