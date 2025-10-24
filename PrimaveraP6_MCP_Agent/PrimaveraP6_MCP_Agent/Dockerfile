# PrimaveraP6 MCP Agent - Dockerfile
# Multi-stage build for production deployment

# ==============================
# Stage 1: Build Dependencies
# ==============================
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# ==============================
# Stage 2: Production Image
# ==============================
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Copy application files
COPY p6_mcp.py .
COPY p6_mcp_phase3_2.py .
COPY requirements.txt .
COPY .env.example .

# Create directory for session storage
RUN mkdir -p /app/data

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8080
ENV SESSION_STORE_FILE=/app/data/session_store.json
ENV P6_VERIFY_SSL=false
ENV AUTO_SESSION_ENABLED=true
ENV AUTO_SESSION_STRICT_MODE=true
ENV ENABLE_SESSION_LOGGING=true

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run the application
CMD ["uvicorn", "p6_mcp_phase3_2:app", "--host", "0.0.0.0", "--port", "8080"]
