# Primavera P6 MCP Agent

A production-ready MCP (Model Context Protocol) server that acts as an intelligent bridge between **ChatGPT / LLM tools** and **Oracle Primavera P6 REST API**.

[![Deploy to Railway](https://railway.app/button.svg)](https://railway.app/new/template?template=https://github.com/akousha/primavera-p6-mcp-agent)

## 🚀 Quick Start

The service is currently deployed at:
- **Production**: https://primavera-p6-mcp-agent-production.up.railway.app
- **MCP Manifest**: https://primavera-p6-mcp-agent-production.up.railway.app/.well-known/mcp.json

### ChatGPT Integration

To add this connector to ChatGPT:
1. Go to ChatGPT Settings → Integrations
2. Add new MCP connector
3. Use the MCP manifest URL: `https://primavera-p6-mcp-agent-production.up.railway.app/.well-known/mcp.json`

## ✅ Features

### 🔐 Authentication & Session Management
- **Smart Login System** - Auto-session management with persistence
- **Session Persistence** - Sessions stored across server restarts
- **Auto-Reconnection** - Automatic re-login on session expiry
- **Session Lifecycle Logging** - Complete audit trail

### 🌐 MCP Tools Available
- **`p6_login`** - Login to Oracle P6 and start a session
- **`p6_session_active`** - Get current active session information
- **`p6_obs_find`** - Fuzzy search OBS by name (LIKE %q%)
- **`p6_projects_by_obs`** - List projects linked to specific OBS
- **`p6_call`** - Generic P6 API proxy call

### 🚀 Advanced Features
- **Auto-Session Mode** - Automatic session ID injection
- **API Key Protection** - Optional shared-secret authentication
- **CORS Support** - Full CORS configuration for browser access
- **Configurable Logging** - Comprehensive logging system
- **SSL Configuration** - Production and development modes

## 📋 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/.well-known/mcp.json` | GET | MCP manifest for ChatGPT integration |
| `/login` | POST | P6 authentication with auto-session |
| `/session/active` | GET | Active session information |
| `/obs/find` | GET | Fuzzy OBS search |
| `/projects/by_obs` | GET | Projects by OBS |
| `/call` | POST | Generic P6 API proxy |
| `/health` | GET | Health check with session status |
| `/tool_schema.json` | GET | Complete tool schema |

## 🛠️ Local Development

### Prerequisites
- Python 3.11+
- Oracle Primavera P6 REST API access

### Installation

```bash
# Clone the repository
git clone https://github.com/akousha/primavera-p6-mcp-agent.git
cd primavera-p6-mcp-agent

# Install dependencies
cd PrimaveraP6_MCP_Agent
pip install -r requirements.txt

# Run the server
uvicorn p6_mcp_phase3_2:app --reload --port 8080
```

### Environment Variables

```bash
# P6 Server Configuration
export P6_BASE_URL="https://your-p6-server.com/p6ws/restapi"
export P6_VERIFY_SSL=true  # Set to false only with self-signed certs

# Session Management
export AUTO_SESSION_ENABLED=true
export AUTO_SESSION_STRICT_MODE=true

# Optional: API Key Protection
# export MCP_API_KEY="your-secret-key"

# Optional: Custom CORS Origins
# export CORS_ORIGINS="https://chatgpt.com,https://your-domain.com"
```

## 🐳 Docker Deployment

### Using Docker

```bash
docker build -t primavera-mcp-agent .
docker run -p 8080:8080 \
  -e P6_BASE_URL="https://your-p6-server.com/p6ws/restapi" \
  primavera-mcp-agent
```

### Using Docker Compose

```bash
# See PrimaveraP6_MCP_Agent/docker-compose.yml for advanced deployment
cd PrimaveraP6_MCP_Agent
docker-compose up -d
```

## ☁️ Cloud Deployment

### Railway (Current Production)

The repository is configured for automatic deployment to Railway:

1. Connect your GitHub repository to Railway
2. Railway will automatically detect the Dockerfile
3. Set environment variables in Railway dashboard
4. Deploy automatically on every push to main

### Other Platforms

- **Render**: Connect GitHub repo, configure environment variables
- **Azure Web Apps**: Deploy using Azure Container Instances
- **Google Cloud Run**: Deploy containerized application

## 🔧 Configuration

### Required Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `P6_BASE_URL` | `https://ca1.p6.oraclecloud.com/metrolinx/p6ws/restapi` | P6 REST API base URL |
| `P6_VERIFY_SSL` | `false` | Enable SSL verification (use `true` in production) |

### Optional Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTO_SESSION_ENABLED` | `true` | Enable automatic session management |
| `AUTO_SESSION_STRICT_MODE` | `true` | Return 401 when no active session |
| `SESSION_STORE_FILE` | `session_store.json` | Session persistence file |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `MCP_API_KEY` | - | Optional API key for authentication |
| `CORS_ORIGINS` | `*` | Allowed CORS origins (comma-separated) |

See `PrimaveraP6_MCP_Agent/PrimaveraP6_MCP_Agent/.env.example` for complete configuration options.

## 📚 Documentation

- **[Detailed README](PrimaveraP6_MCP_Agent/Readme.md)** - Comprehensive documentation
- **[Advanced Features](PrimaveraP6_MCP_Agent/PrimaveraP6_MCP_Agent/README.md)** - Phase 3.2 features
- **[Deployment Guide](PrimaveraP6_MCP_Agent/PrimaveraP6_MCP_Agent/DEPLOYMENT.md)** - Cloud deployment options
- **[Project Summary](PrimaveraP6_MCP_Agent/PrimaveraP6_MCP_Agent/PROJECT_SUMMARY.md)** - Development overview

## 🧪 Testing

### Health Check

```bash
curl https://primavera-p6-mcp-agent-production.up.railway.app/health
```

### MCP Manifest

```bash
curl https://primavera-p6-mcp-agent-production.up.railway.app/.well-known/mcp.json
```

### Login Example

```bash
curl -X POST https://primavera-p6-mcp-agent-production.up.railway.app/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "password": "your_password",
    "databaseName": "your_database",
    "remember": true
  }'
```

## 🔒 Security

- **SSL/TLS**: Enable `P6_VERIFY_SSL=true` in production
- **API Key Protection**: Set `MCP_API_KEY` environment variable
- **CORS Configuration**: Configure `CORS_ORIGINS` for your domain
- **Session Security**: Sessions stored securely with auto-expiry
- **Host Allow Guard**: Prevents unauthorized P6 server access

## 📊 Architecture

```
ChatGPT / LLM Tools
        ↓
  MCP Protocol
        ↓
Primavera P6 MCP Agent (FastAPI)
        ↓
   Session Manager
        ↓
Oracle Primavera P6 REST API
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is open source and available under the MIT License.

## 🆘 Support

For issues or questions:
1. Check the `/health` endpoint for server status
2. Review logs for debugging information
3. Verify P6 server connectivity and credentials
4. Ensure environment configuration is correct

## 🎯 Version

**Current Version**: 0.3.2 (Phase 3.2)
- Production-ready MCP server
- Advanced session management
- Full ChatGPT integration support
- Comprehensive API coverage

---

**Built with ❤️ for seamless Oracle Primavera P6 integration with ChatGPT and LLM tools**
