param([switch]$Stop, [switch]$Open)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$statePath = Join-Path $repoRoot '.cache\preview.json'
if (Test-Path -LiteralPath $statePath) {
    $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
    $serverProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $($state.pid)" -ErrorAction SilentlyContinue
    if ($serverProcess -and $serverProcess.CommandLine.Contains('http.server') -and $serverProcess.CommandLine.Contains($repoRoot)) {
        if ($Stop) {
            $related = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine.Contains("http.server $($state.port)") -and $_.CommandLine.Contains($repoRoot) }
            foreach ($previewProcess in $related) { Stop-Process -Id $previewProcess.ProcessId -ErrorAction SilentlyContinue }
            Remove-Item -LiteralPath $statePath
            Write-Output 'Preview stopped.'
        } else {
            if ($Open) { Start-Process $state.url }
            Write-Output $state.url
        }
        return
    }
}
if ($Stop) { Write-Output 'No preview process is running.'; return }
$siteRoot = Join-Path $repoRoot '_site'
if (-not (Test-Path -LiteralPath (Join-Path $siteRoot 'index.html'))) { throw 'Build the site first: .\scripts\build.ps1' }
$previewPort = $null
foreach ($candidate in @(8000,8001,8002)) {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback,$candidate)
    try { $listener.Start(); $previewPort = $candidate; break } catch { } finally { $listener.Stop() }
}
if ($null -eq $previewPort) { throw 'Ports 8000, 8001, and 8002 are occupied.' }
New-Item -ItemType Directory -Force -Path (Join-Path $repoRoot '.cache') | Out-Null
$process = Start-Process -FilePath (Join-Path $repoRoot '.venv\Scripts\python.exe') -ArgumentList @('-m','http.server',"$previewPort",'--bind','127.0.0.1','--directory',('"' + $siteRoot + '"')) -WorkingDirectory $repoRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $repoRoot '.cache\preview.stdout.log') -RedirectStandardError (Join-Path $repoRoot '.cache\preview.stderr.log')
$previewUrl = "http://127.0.0.1:$previewPort"
@{pid=$process.Id;port=$previewPort;url=$previewUrl;root=$siteRoot} | ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding utf8
$ready=$false
$requestHandler = [System.Net.Http.HttpClientHandler]::new()
$requestHandler.UseProxy = $false
$previewClient = [System.Net.Http.HttpClient]::new($requestHandler)
$previewClient.Timeout = [TimeSpan]::FromSeconds(1)
for ($i=0;$i -lt 20;$i++) {
    try {
        $response = $previewClient.GetAsync($previewUrl).GetAwaiter().GetResult()
        if ($response.IsSuccessStatusCode) { $ready=$true;break }
    } catch { Start-Sleep -Milliseconds 200 }
}
$previewClient.Dispose()
if (-not $ready) { throw 'Preview server did not become ready. See .cache\preview.stderr.log.' }
if ($Open) { Start-Process $previewUrl }
Write-Output $previewUrl
