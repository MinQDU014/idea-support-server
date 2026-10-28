param([switch]$UseDocker)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path $PSScriptRoot -Parent
Push-Location $taskRoot
try {
    $taskEnvFile = Join-Path $taskRoot 'src/main/resources/.env'
    if (-not (Test-Path -LiteralPath $taskEnvFile)) {
        Copy-Item -LiteralPath 'src/main/resources/.env.template' -Destination $taskEnvFile
        Write-Host 'Created resources/.env. Fill in the database password and Gemini API key.'
    }
    if ($UseDocker) {
        docker compose --env-file $taskEnvFile up -d --wait mysql
        if ($LASTEXITCODE -ne 0) { throw 'MySQL startup failed.' }
    } elseif (Test-Path -LiteralPath '.local/mysql-dev-access.json') {
        & .\scripts\start-mysql.ps1
    }
    # Use the verified short Windows temp path for Java AF_UNIX loopback sockets.
    $taskJavaTemp = (Join-Path $env:SystemRoot 'Temp').Replace('\', '/')
    if ($env:JAVA_TOOL_OPTIONS -notmatch 'jdk.net.unixdomain.tmpdir') {
        $env:JAVA_TOOL_OPTIONS = "$env:JAVA_TOOL_OPTIONS -Djdk.net.unixdomain.tmpdir=$taskJavaTemp -Djava.io.tmpdir=$taskJavaTemp"
    }
    & .\gradlew.bat bootRun --args='--spring.profiles.active=local'
    if ($LASTEXITCODE -ne 0) { throw 'Server startup failed.' }
} finally { Pop-Location }
