# agentcore/setup_env.ps1
# Gateway接続用の環境変数を設定するスクリプト

Write-Host "🔧 AgentCore Gateway 環境変数設定" -ForegroundColor Cyan
Write-Host ""

# Gateway URL（固定）
$env:GATEWAY_URL = "https://kb-search-internal-dev-blplmqcf9d.gateway.bedrock-agentcore.ap-northeast-1.amazonaws.com/mcp"

# OAuth認証情報（AWSコンソールから取得）
Write-Host "以下の情報をAWSコンソールのGateway詳細ページから取得してください:" -ForegroundColor Yellow
Write-Host ""

# Client ID
$clientId = Read-Host "GATEWAY_CLIENT_ID を入力"
if ($clientId) {
    $env:GATEWAY_CLIENT_ID = $clientId
}

# Client Secret
$clientSecret = Read-Host "GATEWAY_CLIENT_SECRET を入力"
if ($clientSecret) {
    $env:GATEWAY_CLIENT_SECRET = $clientSecret
}

# Token URL
$tokenUrl = Read-Host "GATEWAY_TOKEN_URL を入力"
if ($tokenUrl) {
    $env:GATEWAY_TOKEN_URL = $tokenUrl
}

Write-Host ""
Write-Host "✅ 環境変数を設定しました:" -ForegroundColor Green
Write-Host "  GATEWAY_URL: $env:GATEWAY_URL" -ForegroundColor White
Write-Host "  GATEWAY_CLIENT_ID: $($env:GATEWAY_CLIENT_ID.Substring(0, [Math]::Min(10, $env:GATEWAY_CLIENT_ID.Length)))..." -ForegroundColor White
Write-Host "  GATEWAY_CLIENT_SECRET: ********" -ForegroundColor White
Write-Host "  GATEWAY_TOKEN_URL: $env:GATEWAY_TOKEN_URL" -ForegroundColor White
Write-Host ""
Write-Host "次のコマンドでエージェントを起動できます:" -ForegroundColor Cyan
Write-Host "  python main.py" -ForegroundColor White
Write-Host ""
Write-Host "注意: この環境変数は現在のPowerShellセッションでのみ有効です" -ForegroundColor Yellow
