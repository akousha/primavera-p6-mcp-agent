# PrimaveraP6 MCP Agent — Phase 3.2 (Production-Ready MCP Server)

This project implements a **production-ready MCP (Middleware Control Point) server** that acts as an intelligent bridge between **ChatGPT / LLM tools** and **Oracle Primavera P6 REST API**. The server provides advanced session management, auto-reconnection, and comprehensive API coverage.

---

## ✅ Features (Phase 3.2 Completed)

### 🔐 **Authentication & Session Management**
- **Smart Login System** — `/login` endpoint with auto-session management
- **Session Persistence** — Sessions stored in JSON file across server restarts
- **Auto-Reconnection** — Automatic re-login on session expiry
- **Session Lifecycle Logging** — Complete audit trail of session events

### 🌐 **API Endpoints**
- **`/login`** — P6 authentication with optional auto-session mode
- **`/call`** — Generic P6 API proxy with automatic session injection
- **`/session/active`** — Get current active session information
- **`/obs/find`** — Fuzzy search OBS by name (LIKE %...% queries)
- **`/obs/byName`** — Exact OBS lookup by name
- **`/projects/list`** — List all projects with filtering and pagination
- **`/projects/by_obs`** — Get projects linked to specific OBS
- **`/health`** — Server health check with session status
- **`/tool_schema.json`** — ChatGPT integration schema

### 🚀 **Advanced Features**
- **Auto-Session Mode** — Automatic session ID injection for all endpoints
- **Strict Mode** - 401 responses when no active session available
- **SSL Configuration** - Configurable SSL verification for development/production
- **Request Timeout Handling** - Configurable timeouts for P6 API calls
- **API Key Enforcement** - Optional shared-secret guard via `MCP_API_KEY`
- **CORS Control** - Allowlist browser origins with `CORS_ORIGINS`
- **Host Allow Guard** - Security protection against unauthorized usage
- **Comprehensive Logging** - Session lifecycle and API call logging

---

## 🚀 Quick Start

### **Option 1: Direct Python (Development)**
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables (optional)
export P6_BASE_URL="https://your-p6-server.com:8443/p6ws"
export P6_VERIFY_SSL=true           # Set to false only when using self-signed certs
export AUTO_SESSION_ENABLED=true
export AUTO_SESSION_STRICT_MODE=true
# export MCP_API_KEY="your-shared-secret"   # Optional

# Run the server
uvicorn p6_mcp_phase3_2:app --reload --port 8080
```

### **Option 2: Docker (Production)**
```bash
# Build and run with Docker Compose
docker-compose up -d

# Or run individual container
docker build -t primavera-mcp-agent .
docker run -p 8080:8080 -e P6_BASE_URL="https://your-p6-server.com:8443/p6ws" primavera-mcp-agent
```

> Copy `.env.example` to `.env` before using Docker commands so the container picks up your credentials and runtime settings.

### **Option 3: Docker Compose (Full Stack)**
```bash
# Production deployment with Nginx
docker-compose --profile nginx up -d

# Development mode with hot reload
docker-compose --profile dev up -d
```

---

## 🔧 Configuration

### **Environment Variables**
Copy `.env.example` to `.env` and configure:

```bash
# P6 Server Configuration
P6_BASE_URL=https://your-p6-server.com:8443/p6ws
P6_ACCEPT=application/json
P6_VERSION=
P6_VERIFY_SSL=true
REQUEST_TIMEOUT=30

# MCP Session Management
AUTO_SESSION_ENABLED=true
AUTO_SESSION_STRICT_MODE=true
SESSION_STORE_FILE=session_store.json

# Runtime (used by Docker/uvicorn wrappers)
MCP_HOST=0.0.0.0
MCP_PORT=8080
# ALLOWED_HOST=your.p6.server.com

# Logging
LOG_LEVEL=INFO
ENABLE_SESSION_LOGGING=true

# Security
MCP_API_KEY=
MCP_API_KEY_HEADER=x-api-key

# ChatGPT Integration
ENABLE_TOOL_SCHEMA=true
TOOL_SERVER_BASE_URL=http://127.0.0.1:8080

# CORS (comma separated, leave blank to disable)
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### **Configuration Files**
- **`.env.example`** — Complete environment configuration template
- **`docker-compose.yml`** — Multi-service deployment with Nginx
- **`nginx.conf`** — Reverse proxy with SSL termination
- **`Dockerfile`** — Multi-stage production build

---

## 🧪 Testing the API

### **1. Health Check**
```bash
curl http://127.0.0.1:8080/health
```

### **2. Login to P6**
```bash
curl -X POST http://127.0.0.1:8080/login \
  -H "Content-Type: application/json" \
  -d '{
        "username": "your_username",
        "password": "your_password",
        "databaseName": "your_database",
        "remember": true
      }'
```

### **3. Auto-Session Mode (No session_id needed!)**
```bash
# With AUTO_SESSION_ENABLED=true, you can omit session_id
curl "http://127.0.0.1:8080/obs/find?q=Admin"
curl "http://127.0.0.1:8080/projects/list"
```

### **4. Manual Session Mode**
```bash
# Get session_id from login response, then use it
curl "http://127.0.0.1:8080/obs/find?session_id=1234567890&q=Admin"
```

---

## 🤖 ChatGPT Integration

### **Tool Schema**
The server exposes a complete tool schema at `/tool_schema.json` for ChatGPT integration:

```json
{
  "tools": [
    {
      "name": "p6_login",
      "description": "Login to Oracle P6 and start a session"
    },
    {
      "name": "p6_obs_find", 
      "description": "Fuzzy search OBS by name"
    },
    {
      "name": "p6_projects_list",
      "description": "List all projects with filtering"
    },
    {
      "name": "p6_projects_by_obs",
      "description": "Get projects linked to specific OBS"
    },
    {
      "name": "p6_call",
      "description": "Generic P6 API call through MCP proxy"
    }
  ]
}
```

### **ChatGPT Setup**
1. Configure ChatGPT to use this MCP server
2. Point to `http://your-server:8080/tool_schema.json`
3. ChatGPT will automatically discover and use the available tools

---

## 🚀 Deployment Options

### **Local Development**
```bash
uvicorn p6_mcp_phase3_2:app --reload --port 8080
```

### **Docker Production**
```bash
docker-compose up -d
```

### **Cloud Deployment**

#### **Railway**
```bash
# Deploy to Railway
railway login
railway init
railway up
```

#### **Render**
```bash
# Connect GitHub repo to Render
# Set environment variables in Render dashboard
# Deploy automatically on git push
```

#### **Azure Web App**
```bash
# Deploy to Azure Container Instances
az container create --resource-group myResourceGroup \
  --name primavera-mcp-agent \
  --image your-registry/primavera-mcp-agent \
  --ports 8080
```

---

## 📊 Monitoring & Logging

### **Health Monitoring**
- **`/health`** endpoint provides server and session status
- Docker health checks configured
- Nginx upstream health monitoring

### **Logging**
- Session lifecycle events
- API call logging
- Error tracking and debugging
- Configurable log levels

### **Metrics**
- Request/response times
- Session creation/expiry events
- Error rates and types
- P6 API call success/failure rates

---

## 🔒 Security Features

### **Authentication**
- P6 credential validation
- Session-based authentication
- Optional API key protection

### **Network Security**
- Host allow guard (prevents unauthorized usage)
- CORS configuration
- Optional API key header enforcement
- SSL/TLS termination at Nginx

### **Data Protection**
- Session persistence stored on disk (`SESSION_STORE_FILE` / Docker volume)
- Optional credential retention only when `remember=true`
- Session lifecycle logging for traceability

---

## 🛠️ Development

### **Project Structure**
```
PrimaveraP6_MCP_Agent/
├── p6_mcp.py                    # Phase 3.1 (backup)
├── p6_mcp_phase3_2.py          # Phase 3.2 (current)
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Container build
├── docker-compose.yml          # Multi-service deployment
├── nginx.conf                  # Reverse proxy config
├── .env.example               # Environment template
└── README.md                  # This file
```

### **Development Workflow**
1. **Local Development**: Use `uvicorn` with `--reload`
2. **Testing**: Use Docker Compose with dev profile
3. **Production**: Use Docker Compose with nginx profile
4. **Cloud**: Deploy using platform-specific methods

---

## 🎯 Next Steps (Future Phases)

### **Phase 4: API Expansion**
- `/activities` endpoint
- `/wbs` (Work Breakdown Structure) endpoint  
- `/resources` endpoint
- `/eps` (Enterprise Project Structure) endpoint
- `/assignments` endpoint
- `/codes` endpoint

### **Phase 5: Response Standardization**
- Consistent JSON response format
- Error wrapping and standardization
- Response caching for performance

### **Phase 6: UI Integration**
- React/Streamlit frontend
- Interactive project dashboard
- Real-time session monitoring

### **Phase 7: Advanced Features**
- Webhook support for P6 events
- Data synchronization
- Advanced reporting and analytics
- Multi-tenant support

---

## 📞 Support

For issues, questions, or contributions:
- Check the `/health` endpoint for server status
- Review logs for debugging information
- Ensure P6 server connectivity and credentials
- Verify environment configuration

---

**🎉 This is a production-ready MCP server with advanced session management, comprehensive API coverage, and full deployment support!**
