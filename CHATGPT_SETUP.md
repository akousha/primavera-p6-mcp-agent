# ChatGPT MCP Connector Setup Guide

This guide walks you through adding the Primavera P6 MCP Agent to ChatGPT as a connector.

## ✅ Prerequisites

Before adding to ChatGPT, verify:

1. **Service is Deployed and Running**
   ```bash
   curl https://primavera-p6-mcp-agent-production.up.railway.app/health
   ```
   Expected response: `{"ok": true, ...}`

2. **MCP Manifest is Accessible**
   ```bash
   curl https://primavera-p6-mcp-agent-production.up.railway.app/.well-known/mcp.json
   ```
   Expected: Valid JSON with service name and tools list

3. **CORS is Configured**
   - Default: Wildcard `*` (allows all origins)
   - Production: Set `CORS_ORIGINS` to specific domains

## 🚀 Adding to ChatGPT

### Step 1: Access ChatGPT Settings

1. Open ChatGPT (https://chatgpt.com)
2. Click your profile icon → Settings
3. Navigate to **Integrations** or **Connectors** section

### Step 2: Add MCP Connector

1. Click **"Add Connector"** or **"Add Integration"**
2. Select **"MCP (Model Context Protocol)"** if available
3. Enter the MCP manifest URL:
   ```
   https://primavera-p6-mcp-agent-production.up.railway.app/.well-known/mcp.json
   ```

### Step 3: Verify Connection

1. ChatGPT will fetch the manifest and discover available tools
2. Verify these 5 tools are listed:
   - ✅ `p6_login` - Login to Oracle P6
   - ✅ `p6_session_active` - Get active session
   - ✅ `p6_obs_find` - Search OBS by name
   - ✅ `p6_projects_by_obs` - List projects by OBS
   - ✅ `p6_call` - Generic P6 API proxy

3. Save/Activate the connector

## 🧪 Testing the Integration

### Test 1: Login to P6

Ask ChatGPT:
```
Login to Primavera P6 with username "your_username", password "your_password", 
and database "your_database". Remember my credentials.
```

Expected: Session ID returned and stored

### Test 2: Search OBS

Ask ChatGPT:
```
Find all OBS entries containing "Admin"
```

Expected: List of matching OBS entries

### Test 3: List Projects

Ask ChatGPT:
```
Show me all projects under the Admin-SB OBS
```

Expected: List of projects with details

## 🔧 Troubleshooting

### Issue: "Cannot connect to service"

**Causes:**
- Service is down
- CORS blocking the request
- Network/firewall issues

**Solutions:**
1. Check service health: `curl https://primavera-p6-mcp-agent-production.up.railway.app/health`
2. Verify CORS headers: `curl -I https://primavera-p6-mcp-agent-production.up.railway.app/.well-known/mcp.json`
3. Check Railway deployment status
4. Review Railway logs for errors

### Issue: "Manifest not found" (404 error)

**Causes:**
- Wrong URL
- Service not deployed
- Dockerfile using wrong app version

**Solutions:**
1. Verify URL exactly matches: `/.well-known/mcp.json` (not `/mcp.json` or `/manifest`)
2. Check Dockerfile CMD uses: `p6_mcp_phase3_2:app`
3. Redeploy on Railway

### Issue: "Tools not appearing in ChatGPT"

**Causes:**
- Manifest format incorrect
- ChatGPT cache
- Connector not activated

**Solutions:**
1. Validate manifest JSON: `curl ... | jq .`
2. Remove and re-add connector in ChatGPT
3. Clear browser cache
4. Try in incognito/private mode

### Issue: "Login fails" or "401 Unauthorized"

**Causes:**
- Incorrect P6 credentials
- P6 server not accessible
- API key required but not set

**Solutions:**
1. Verify P6 credentials are correct
2. Check P6_BASE_URL in Railway environment variables
3. If MCP_API_KEY is set, include it in requests
4. Check P6 server is accessible from Railway

## 📊 Monitoring

### Check Service Health
```bash
curl https://primavera-p6-mcp-agent-production.up.railway.app/health
```

### View Railway Logs
1. Go to Railway dashboard
2. Select your project
3. Click "Logs" tab
4. Filter by log level (INFO, WARNING, ERROR)

### Monitor Session Activity
- Check logs for "Session created" messages
- Monitor "Auto-reconnect" events
- Review failed login attempts

## 🔒 Security Considerations

### For Public Access
If your connector is publicly accessible:

1. **Enable API Key Protection**
   ```bash
   # In Railway, set environment variable:
   MCP_API_KEY=your-secret-key-here
   ```

2. **Restrict CORS Origins**
   ```bash
   # In Railway, set environment variable:
   CORS_ORIGINS=https://chatgpt.com,https://chat.openai.com
   ```

3. **Enable SSL Verification**
   ```bash
   P6_VERIFY_SSL=true
   ```

### For Internal/Private Use
If behind a firewall or VPN:

1. CORS wildcard is acceptable
2. API key optional but recommended
3. Verify network access policies

## 📝 Configuration Reference

### Required Environment Variables (Railway)
```bash
P6_BASE_URL=https://your-p6-server.com/p6ws/restapi
```

### Recommended for Production
```bash
P6_VERIFY_SSL=true
MCP_API_KEY=your-secret-key
CORS_ORIGINS=https://chatgpt.com
LOG_LEVEL=INFO
AUTO_SESSION_ENABLED=true
AUTO_SESSION_STRICT_MODE=true
```

## 🎯 Next Steps

After successful integration:

1. **Test All Tools**
   - Login/logout
   - OBS search
   - Project listing
   - Generic API calls

2. **Set Up Monitoring**
   - Enable Railway metrics
   - Configure log aggregation
   - Set up uptime monitoring

3. **Share with Team**
   - Document usage examples
   - Create common query templates
   - Train users on available tools

## 📞 Support

### Documentation
- [Main README](README.md)
- [Security Policy](SECURITY.md)
- [Contributing Guide](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)

### Resources
- Production URL: https://primavera-p6-mcp-agent-production.up.railway.app
- MCP Manifest: https://primavera-p6-mcp-agent-production.up.railway.app/.well-known/mcp.json
- Health Check: https://primavera-p6-mcp-agent-production.up.railway.app/health

### Getting Help
1. Check Railway logs for errors
2. Review security policy for best practices
3. Open GitHub issue for bugs
4. Create discussion for questions

---

**Success!** 🎉 Your Primavera P6 MCP Agent is now integrated with ChatGPT and ready to use!
