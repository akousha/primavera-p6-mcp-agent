# PrimaveraP6_MCP_Agent — Phase 1 (Local FastAPI MCP Server)

This project implements a **local MCP (Middleware Control Point) server** to act as a bridge between **ChatGPT / LLM tools** and **Oracle Primavera P6 REST API**.

---

## ✅ Features (Phase 1 Completed)

- `/login` endpoint — performs **P6 custom login** using `username`, `password`, `DatabaseName`
- Extracts and stores **cookies + optional AuthToken**
- Returns a **session_id** to reuse
- `/call` endpoint — forwards **any API request to P6** using stored session automatically
- Enforces **host allow guard** to prevent misuse
- Includes **`tool_schema.json`** to integrate with ChatGPT **Custom Tools / MCP Connectors**

---

## 🚀 How to Run (Simple — System Python Mode)

```bash
pip install fastapi uvicorn requests pydantic
uvicorn p6_mcp:app --reload --port 8080
```

> Optional: set optional environment variables before running:

```bash
export P6_BASE_URL="https://ca1.p6.oraclecloud.com/metrolinx/p6ws/restapi"
export P6_ACCEPT="application/json"
export P6_VERSION=""     # Example: "23.12.0" if Oracle requires it
```

---

## 🎯 Test Login (Replace credentials accordingly)

```bash
curl -X POST http://127.0.0.1:8080/login \
  -H "Content-Type: application/json" \
  -d '{
        "username": "armank",
        "password": "your_password",
        "databaseName": "MetrolinxProductionDB"
      }'
```

Response will return:

```json
{
  "session_id": "1738655293356",
  "cookies": "JSESSIONID=...; PSESSIONAFFINITYID=...",
  "authToken": null
}
```

---

## 📌 Example `/call` Request (OBS Lookup)

```bash
curl -X POST http://127.0.0.1:8080/call \
  -H "Content-Type: application/json" \
  -d '{
        "session_id": "1738655293356",
        "method": "GET",
        "path": "/obs",
        "query": {
            "Filter": "Name=\"Admin-SB\"",
            "Fields": "Name,ObjectId,GUID",
            "OrderBy": ""
        }
      }'
```

---

## 🎯 Next Steps (Phase 2 Roadmap)

- Auto re-login on session expiry
- Friendly helper functions like `p6_list_projects()`
- Expanded ChatGPT Tool Schema (per endpoint instead of raw `/call`)
- Ready for **online deployment** (Render / Railway / Azure Web App)
- Convert into **Custom ChatGPT MCP Connector** format

---

🧠 **This is your base — next we layer intelligence on top.**
