# PrimaveraP6 MCP Agent - Deployment Guide

This guide covers deploying the PrimaveraP6 MCP Agent to various cloud platforms and environments.

---

## 🚀 Quick Deployment Options

| Platform | Difficulty | Cost | Best For |
|----------|------------|------|----------|
| **Railway** | ⭐ Easy | Free tier available | Quick prototypes |
| **Render** | ⭐⭐ Medium | Free tier available | Production apps |
| **Azure Container Instances** | ⭐⭐⭐ Advanced | Pay-per-use | Enterprise |
| **Docker + VPS** | ⭐⭐⭐⭐ Expert | VPS cost | Full control |

---

## 🚂 Railway Deployment

### **Step 1: Prepare Repository**
```bash
# Ensure your code is in a Git repository
git init
git add .
git commit -m "Initial PrimaveraP6 MCP Agent"
git push origin main
```

### **Step 2: Deploy to Railway**
1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your repository
5. Railway will auto-detect the Dockerfile

### **Step 3: Configure Environment Variables**
In Railway dashboard, add these environment variables:

```bash
# Required
P6_BASE_URL=https://your-p6-server.com:8443/p6ws
P6_VERIFY_SSL=true

# Optional
AUTO_SESSION_ENABLED=true
AUTO_SESSION_STRICT_MODE=true
LOG_LEVEL=INFO
ENVIRONMENT=production
```

### **Step 4: Deploy**
- Railway automatically builds and deploys
- Get your app URL: `https://your-app.railway.app`
- Test: `curl https://your-app.railway.app/health`

### **Railway Configuration Files**
Create `railway.json` (optional):
```json
{
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "startCommand": "uvicorn p6_mcp_phase3_2:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/health"
  }
}
```

---

## 🎨 Render Deployment

### **Step 1: Connect Repository**
1. Go to [render.com](https://render.com)
2. Sign up with GitHub
3. Click "New" → "Web Service"
4. Connect your GitHub repository

### **Step 2: Configure Service**
```yaml
# render.yaml (optional)
services:
  - type: web
    name: primavera-mcp-agent
    env: docker
    dockerfilePath: ./Dockerfile
    envVars:
      - key: P6_BASE_URL
        value: https://your-p6-server.com:8443/p6ws
      - key: P6_VERIFY_SSL
        value: true
      - key: AUTO_SESSION_ENABLED
        value: true
      - key: ENVIRONMENT
        value: production
```

### **Step 3: Environment Variables**
In Render dashboard, set:
- `P6_BASE_URL` = Your P6 server URL
- `P6_VERIFY_SSL` = `true` (for production)
- `AUTO_SESSION_ENABLED` = `true`
- `LOG_LEVEL` = `INFO`

### **Step 4: Deploy**
- Render builds from Dockerfile
- Service starts automatically
- Get URL: `https://your-app.onrender.com`

---

## ☁️ Azure Container Instances

### **Step 1: Create Resource Group**
```bash
# Login to Azure
az login

# Create resource group
az group create --name primavera-mcp-rg --location eastus
```

### **Step 2: Build and Push Container**
```bash
# Build Docker image
docker build -t primavera-mcp-agent .

# Tag for Azure Container Registry
docker tag primavera-mcp-agent your-registry.azurecr.io/primavera-mcp-agent:latest

# Push to registry
docker push your-registry.azurecr.io/primavera-mcp-agent:latest
```

### **Step 3: Deploy Container**
```bash
# Deploy to Azure Container Instances
az container create \
  --resource-group primavera-mcp-rg \
  --name primavera-mcp-agent \
  --image your-registry.azurecr.io/primavera-mcp-agent:latest \
  --ports 8080 \
  --environment-variables \
    P6_BASE_URL=https://your-p6-server.com:8443/p6ws \
    P6_VERIFY_SSL=true \
    AUTO_SESSION_ENABLED=true \
    ENVIRONMENT=production \
  --cpu 1 \
  --memory 2
```

### **Step 4: Get Public IP**
```bash
# Get container IP
az container show --resource-group primavera-mcp-rg --name primavera-mcp-agent --query ipAddress.ip --output tsv
```

---

## 🐳 Docker Deployment

### **Local Docker**
```bash
# Build image
docker build -t primavera-mcp-agent .

# Run container
docker run -p 8080:8080 \
  -e P6_BASE_URL=https://your-p6-server.com:8443/p6ws \
  -e P6_VERIFY_SSL=true \
  -e AUTO_SESSION_ENABLED=true \
  primavera-mcp-agent
```

### **Docker Compose (Production)**
```bash
# Create .env file
cp .env.example .env
# Edit .env with your values

# Deploy with Nginx
docker-compose --profile nginx up -d

# Check status
docker-compose ps
```

### **Docker Swarm**
```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.yml primavera-mcp
```

---

## 🔧 Environment Configuration

### **Required Variables**
```bash
# P6 Server (Required)
P6_BASE_URL=https://your-p6-server.com:8443/p6ws
P6_VERIFY_SSL=true  # false for development

# MCP Server (Required)
MCP_HOST=0.0.0.0
MCP_PORT=8080
```

### **Optional Variables**
```bash
# Session Management
AUTO_SESSION_ENABLED=true
AUTO_SESSION_STRICT_MODE=true
SESSION_STORE_FILE=/app/data/session_store.json

# Logging
LOG_LEVEL=INFO
ENABLE_SESSION_LOGGING=true

# Security
MCP_API_KEY=your-secret-key
MCP_API_KEY_HEADER=x-api-key
CORS_ORIGINS=https://your-frontend.com

# Integration
ENABLE_TOOL_SCHEMA=true
TOOL_SERVER_BASE_URL=https://your-public-mcp.example.com

# Performance
REQUEST_TIMEOUT=30
```

---

## 🔒 Security Considerations

### **Production Security**
1. **SSL/TLS**: Always use HTTPS in production
2. **API Keys**: Set `MCP_API_KEY` for authentication
3. **CORS**: Configure `CORS_ORIGINS` for your frontend
4. **Host Guard**: Ensure `ALLOWED_HOST` matches your Primavera P6 domain
5. **Network**: Use private networks when possible

### **Environment-Specific Settings**
```bash
# Development
P6_VERIFY_SSL=false
LOG_LEVEL=DEBUG
ENVIRONMENT=development

# Staging
P6_VERIFY_SSL=true
LOG_LEVEL=INFO
ENVIRONMENT=staging

# Production
P6_VERIFY_SSL=true
LOG_LEVEL=WARNING
ENVIRONMENT=production
MCP_API_KEY=your-production-key
```

---

## 📊 Monitoring & Health Checks

### **Health Check Endpoint**
```bash
# Basic health check
curl https://your-app.com/health

# Expected response
{
  "ok": true,
  "time": 1738655293,
  "base": "https://your-p6-server.com:8443/p6ws",
  "sessions": [...]
}
```

### **Monitoring Setup**
1. **Uptime Monitoring**: Use UptimeRobot or similar
2. **Log Aggregation**: Send logs to Azure Monitor, CloudWatch, etc.
3. **Metrics**: Monitor CPU, memory, request rates
4. **Alerts**: Set up alerts for health check failures

### **Docker Health Checks**
```dockerfile
# Already configured in Dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1
```

---

## 🚨 Troubleshooting

### **Common Issues**

#### **1. SSL Certificate Errors**
```bash
# For development
P6_VERIFY_SSL=false

# For production - ensure P6 server has valid SSL
P6_VERIFY_SSL=true
```

#### **2. Session Expiry**
```bash
# Enable auto-session mode
AUTO_SESSION_ENABLED=true
AUTO_SESSION_STRICT_MODE=true
```

#### **3. Port Binding Issues**
```bash
# Use environment variable for port
MCP_PORT=$PORT  # Railway/Render set this automatically
```

#### **4. Memory Issues**
```bash
# Increase container memory
docker run --memory=2g primavera-mcp-agent
```

### **Debug Commands**
```bash
# Check container logs
docker logs primavera-mcp-agent

# Check health
curl https://your-app.com/health

# Test tool schema
curl https://your-app.com/tool_schema.json
```

---

## 🔄 CI/CD Pipeline

### **GitHub Actions Example**
```yaml
# .github/workflows/deploy.yml
name: Deploy to Railway
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to Railway
        run: |
          # Railway CLI deployment
          railway login --token ${{ secrets.RAILWAY_TOKEN }}
          railway up
```

### **GitLab CI Example**
```yaml
# .gitlab-ci.yml
deploy:
  stage: deploy
  script:
    - docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA .
    - docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
    - az container create --resource-group $AZURE_RG --name primavera-mcp-agent --image $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
```

---

## 📈 Scaling Considerations

### **Horizontal Scaling**
- Use load balancer (Nginx, Azure Load Balancer)
- Multiple container instances
- Session storage in Redis (future enhancement)

### **Vertical Scaling**
- Increase CPU/memory allocation
- Optimize request timeouts
- Enable response caching

### **Database Considerations**
- P6 server connection limits
- Session storage optimization
- Connection pooling (future enhancement)

---

## 🎯 Next Steps

1. **Deploy to your chosen platform**
2. **Configure environment variables**
3. **Test all endpoints**
4. **Set up monitoring**
5. **Configure ChatGPT integration**
6. **Scale as needed**

---

**🚀 Your PrimaveraP6 MCP Agent is now ready for production deployment!**
