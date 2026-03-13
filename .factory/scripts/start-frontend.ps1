Set-Location C:\EthicalSiteInspector\frontend
$proc = Start-Process -FilePath "cmd" -ArgumentList "/c", "npx vite --port 5173 --host 127.0.0.1" -NoNewWindow -PassThru
Write-Host "Frontend PID: $($proc.Id)"
Start-Sleep -Seconds 12
$result = Invoke-WebRequest -Uri "http://127.0.0.1:5173" -UseBasicParsing -ErrorAction SilentlyContinue
if ($result.StatusCode -eq 200) {
    Write-Host "FRONTEND_STARTED"
} else {
    Write-Host "FRONTEND_FAILED"
}
