# agentcore/deploy.ps1
# AgentCore Runtime deploy script
# Overwrites the same agent every time

$AGENT_NAME = "kb_search_agent"
$REGION = "ap-northeast-1"

Write-Host "[Deploy] AgentCore Runtime" -ForegroundColor Cyan
Write-Host "Agent: $AGENT_NAME"
Write-Host "Region: $REGION"
Write-Host ""

# Configure
Write-Host "[1/2] Configuring..." -ForegroundColor Yellow
agentcore configure --entrypoint app.py --name $AGENT_NAME --region $REGION --non-interactive

# Deploy (auto-update if exists)
Write-Host ""
Write-Host "[2/2] Deploying (auto-update)..." -ForegroundColor Yellow
agentcore launch --auto-update-on-conflict

Write-Host ""
Write-Host "[Done] Deploy completed!" -ForegroundColor Green
Write-Host ""
Write-Host "Test command:"
Write-Host "  agentcore invoke '{""prompt"": ""Hello""}'"
