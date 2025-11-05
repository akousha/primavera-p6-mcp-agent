# Deployment script for PrimaveraP6 MCP Agent
# This script helps deploy the updated MCP agent to Railway

Write-Host "🚀 PrimaveraP6 MCP Agent - Deployment Script" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green

# Check if we're in a git repository
if (-not (Test-Path ".git")) {
    Write-Host "❌ Error: This is not a git repository. Please run 'git init' first." -ForegroundColor Red
    exit 1
}

# Check git status
Write-Host "📊 Checking git status..." -ForegroundColor Yellow
$gitStatus = git status --porcelain
if ($gitStatus) {
    Write-Host "📁 Found uncommitted changes:" -ForegroundColor Yellow
    git status --short
    
    $commit = Read-Host "Do you want to commit these changes? (y/N)"
    if ($commit -eq "y" -or $commit -eq "Y") {
        Write-Host "📝 Adding all changes..." -ForegroundColor Yellow
        git add .
        
        $message = Read-Host "Enter commit message (default: 'Update MCP manifest and CORS handling for ChatGPT integration')"
        if (-not $message) {
            $message = "Update MCP manifest and CORS handling for ChatGPT integration"
        }
        
        Write-Host "💾 Committing changes..." -ForegroundColor Yellow
        git commit -m $message
    }
}

# Push to repository
Write-Host "🔄 Pushing to repository..." -ForegroundColor Yellow
try {
    git push origin main
    Write-Host "✅ Successfully pushed to repository!" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to push. Error: $_" -ForegroundColor Red
    Write-Host "💡 Make sure you have set up the remote repository correctly." -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "🎉 Deployment completed!" -ForegroundColor Green
Write-Host "⏱️  Railway will automatically detect and deploy the changes." -ForegroundColor Yellow
Write-Host "🔗 Your MCP manifest will be available at:" -ForegroundColor Yellow
Write-Host "   https://primavera-p6-mcp-agent-production.up.railway.app/.well-known/mcp.json" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Yellow
Write-Host "   1. Wait for Railway deployment to complete (check logs)" -ForegroundColor White
Write-Host "   2. Test the MCP manifest endpoint in your browser" -ForegroundColor White
Write-Host "   3. Try adding the connector to ChatGPT again" -ForegroundColor White
Write-Host ""
Write-Host "🆘 If you still get timeout errors:" -ForegroundColor Yellow
Write-Host "   - Check Railway deployment logs" -ForegroundColor White
Write-Host "   - Verify the health endpoint: /health" -ForegroundColor White
Write-Host "   - Ensure your Railway domain is accessible" -ForegroundColor White