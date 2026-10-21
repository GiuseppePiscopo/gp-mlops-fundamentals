param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$Username
)

$ErrorActionPreference = "Stop"

$remoteUrl = "https://bitbucket.org/braincrumbz/mlops-fundamentals-poc.git"

git remote set-url origin $remoteUrl
if ($LASTEXITCODE -ne 0) {
    throw "Failed to set the origin remote URL."
}

git remote set-url --push origin $remoteUrl
if ($LASTEXITCODE -ne 0) {
    throw "Failed to set the origin push URL."
}

git config --local --replace-all credential.helper ""
if ($LASTEXITCODE -ne 0) {
    throw "Failed to reset the local credential helper."
}

git config --local --add credential.helper wincred
if ($LASTEXITCODE -ne 0) {
    throw "Failed to configure the wincred credential helper."
}

git config --local credential.https://bitbucket.org.username $Username
if ($LASTEXITCODE -ne 0) {
    throw "Failed to configure the Bitbucket username."
}

$secureToken = Read-Host "API token Bitbucket" -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureToken)
$token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
try {
    @(
        "protocol=https",
        "host=bitbucket.org",
        "username=$Username",
        "password=$token"
    ) | git credential-wincred store
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to store the Bitbucket API token."
    }
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    Remove-Variable secureToken, bstr, token -ErrorAction SilentlyContinue
}

Write-Host "Git remote configured. Run .\tools\Test-GitRemote.ps1 to verify."
