$ErrorActionPreference = 'Stop'
$secureKey = Read-Host 'Meshy API key (input hidden; never paste into chat)' -AsSecureString
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
try {
    $plainKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    if (-not $plainKey.StartsWith('msy_')) { throw 'Expected a Meshy API key beginning with msy_' }
    [Environment]::SetEnvironmentVariable('MESHY_API_KEY', $plainKey, 'User')
    Write-Output 'Meshy API key saved in your local Windows user environment. Key value is not printed.'
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    $plainKey = $null
    $secureKey.Dispose()
}
