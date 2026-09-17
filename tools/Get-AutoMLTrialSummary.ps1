param(
    [Parameter(Mandatory = $true)]
    [string]$JobName
)

$ErrorActionPreference = "Stop"

$tags = $null
for ($attempt = 1; $attempt -le 5; $attempt++) {
    $tagsJson = az ml job show --name $JobName --query tags -o json 2>$null
    if ($LASTEXITCODE -eq 0 -and $tagsJson) {
        $tags = $tagsJson | ConvertFrom-Json
        break
    }
    Write-Host "Attempt $attempt failed (exit $LASTEXITCODE), retrying..."
    Start-Sleep -Seconds 2
}

if (-not $tags) {
    Write-Host "All attempts failed to fetch job tags."
    exit 1
}

$iterations = $tags.iteration_000 -split ';'
$algorithms = $tags.run_algorithm_000 -split ';'
$scores = $tags.score_000 -split ';'
$fitTimes = $tags.fit_time_000 -split ';'

$rows = for ($i = 0; $i -lt $iterations.Count; $i++) {
    [PSCustomObject]@{
        Iteration  = $iterations[$i]
        Algorithm  = $algorithms[$i]
        Score      = [double]$scores[$i]
        FitTimeSec = $fitTimes[$i]
    }
}

$rows | Sort-Object Score | Format-Table -AutoSize
