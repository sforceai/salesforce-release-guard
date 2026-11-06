$ErrorActionPreference = 'Stop'
$projectDirectory = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectDirectory
try {
    $demoResult = & python -m salesforce_guard scan (Join-Path $projectDirectory 'examples/risky-project') --output (Join-Path $projectDirectory 'output')
    if ($LASTEXITCODE -ne 0) { throw 'Demo scan did not complete. See the message above.' }
    $demoReport = ($demoResult -join "`n") | ConvertFrom-Json
    Write-Host 'Salesforce Guard demonstration completed. Opening the local report.'
    Start-Process -FilePath $demoReport.report
} finally {
    Pop-Location
}
