[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$Executable,
    [string]$Map = $env:TOWNAGE_MAP,
    [string]$Port = $env:TOWNAGE_PORT,
    [string[]]$ServerArguments = @()
)

$ErrorActionPreference = 'Stop'

if (-not $Map) { $Map = '/Game/Maps/L_VillageTerrain_01' }
if (-not $Port) { $Port = '7777' }

if ($Map -cnotmatch '^/Game(/[A-Za-z0-9_]+)+$') {
    throw 'Map must be a cooked /Game package path, for example /Game/Maps/L_VillageTerrain_01.'
}

[int]$portNumber = 0
if ($Port -notmatch '^[0-9]{1,5}$' -or -not [int]::TryParse($Port, [ref]$portNumber) -or
    $portNumber -lt 1 -or $portNumber -gt 65535) {
    throw 'Port must be an integer from 1 through 65535.'
}

if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) {
    throw "Server executable not found: $Executable"
}

$serverPath = (Resolve-Path -LiteralPath $Executable).ProviderPath
$launchArguments = @($Map, "-port=$portNumber", '-unattended', '-stdout', '-FullStdOutLogOutput') + $ServerArguments
& $serverPath @launchArguments
exit $LASTEXITCODE
