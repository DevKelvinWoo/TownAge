$ErrorActionPreference = 'Stop'
if (-not $env:MESHY_API_KEY) {
    $env:MESHY_API_KEY = [Environment]::GetEnvironmentVariable('MESHY_API_KEY', 'User')
}
$serverPath = Join-Path $env:USERPROFILE '.codex/mcp/meshy/node_modules/@meshy-ai/meshy-mcp-server/dist/index.js'
if (-not (Test-Path -LiteralPath $serverPath)) { throw 'Install the pinned official Meshy MCP package first; see README.' }
# The official server can expose its tool catalog without a key. Authentication
# is checked by Meshy on API calls. Keep stdout exclusively for MCP JSON-RPC.
& 'C:/Program Files/nodejs/node.exe' $serverPath
exit $LASTEXITCODE
