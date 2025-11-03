FROM python:3.11-slim

WORKDIR /app

COPY PrimaveraP6_MCP_Agent/ .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

CMD ["uvicorn", "p6_mcp_phase3_2:app", "--host", "0.0.0.0", "--port", "8080"]
