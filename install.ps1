param([Parameter(Mandatory=$true)][string]$Target,[switch]$Force)
$here=Split-Path -Parent $MyInvocation.MyCommand.Path
$python=Get-Command python -ErrorAction SilentlyContinue
if(-not $python){throw 'Python 3.9+ required. Install Python and retry.'}
$arguments=@((Join-Path $here 'install.py'), $Target)
if($Force){$arguments+='--force'}
& python @arguments
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
