param(
    [string]$RemoteName = "origin"
)

$ErrorActionPreference = "Stop"

$remoteUrls = @(git remote get-url --all $RemoteName)
if ($LASTEXITCODE -ne 0) {
    throw "Remote '$RemoteName' not found."
}

$remoteUrls | ForEach-Object { Write-Host "Remote URL: $_" }

if ($remoteUrls -match '^https?://[^/@]+@') {
    throw "Remote URL contains a username."
}

$previousPrompt = $env:GIT_TERMINAL_PROMPT
$previousInteractive = $env:GCM_INTERACTIVE
$env:GIT_TERMINAL_PROMPT = "0"
$env:GCM_INTERACTIVE = "never"
try {
    git ls-remote $RemoteName
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to read remote '$RemoteName'. Check the remote URL and credentials."
    }
}
finally {
    $env:GIT_TERMINAL_PROMPT = $previousPrompt
    $env:GCM_INTERACTIVE = $previousInteractive
}

Write-Host "Remote verification succeeded."
