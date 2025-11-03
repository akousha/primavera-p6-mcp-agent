from __future__ import annotations
import os
import time
from datetime import datetime
import json
import urllib.parse
from typing import Optional, Dict, Any, List, Tuple

import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ==============================
# CONFIG
# ==============================
P6_BASE_URL = os.getenv("P6_BASE_URL", "https://ca1.p6.oraclecloud.com/metrolinx/p6ws/restapi")
P6_ACCEPT = os.getenv("P6_ACCEPT", "application/json")
P6_VERSION = os.getenv("P6_VERSION", "")  # e.g., "23.12.0" if Oracle requires it
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "30"))

ALLOWED_HOST = (P6_BASE_URL.split("//", 1)[-1]).split("/", 1)[0]


# ==============================
# SESSION STORE (LOCAL / IN-MEMORY)
# ==============================
class SavedCreds(BaseModel):
    username: str
    password: str
    database_name: str


class Session(BaseModel):
    cookies: str
    auth_token: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    database_name: Optional[str] = None
    # Optional, only if user opts-in at login ("remember": true)
    creds: Optional[SavedCreds] = None


SESSIONS: Dict[str, Session] = {}


def _mk_session_id() -> str:
    return str(int(time.time() * 1000))


# ==============================
# REQUEST SCHEMAS
# ==============================
class LoginRequest(BaseModel):
    username: str
    password: str
    databaseName: str
    # If true, we store creds in memory to support auto-relogin on 401.
    remember: bool = False


class LoginResponse(BaseModel):
    session_id: str
    cookies: str
    authToken: Optional[str] = None
    remember: bool = False


class CallRequest(BaseModel):
    session_id: str
    method: str = Field(pattern=r"^(GET|POST|PUT|PATCH|DELETE)$")
    path: str  # e.g. "/obs" or "/projects/123"
    query: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, str]] = None
    body: Optional[Any] = None


class ProxyResponse(BaseModel):
    status: int
    headers: Dict[str, Any]
    body: Any


# ==============================
# FASTAPI APP
# ==============================
app = FastAPI(title="P6 MCP Server", version="0.3.0 (Phase 3)")

# Add CORS middleware to allow ChatGPT and other clients to access the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for MCP compatibility
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------
# Utilities
# ------------------------------
def _build_target_url(path: str, query: Optional[Dict[str, Any]]) -> str:
    path = path if path.startswith("/") else f"/{path}"
    base = P6_BASE_URL.rstrip("/")
    params = query.copy() if query else {}
    return f"{base}{path}?{urllib.parse.urlencode(params, doseq=True)}" if params else f"{base}{path}"


def _default_headers(ses: Session, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    headers = {
        "Accept": P6_ACCEPT,
        "Cookie": ses.cookies,
    }
    if P6_VERSION:
        headers["Version"] = P6_VERSION
    if ses.auth_token:
        headers["AuthToken"] = ses.auth_token
    if extra:
        headers.update(extra)
    return headers


def _extract_cookies(resp: requests.Response) -> str:
    pairs: List[str] = []
    for c in resp.cookies:
        pairs.append(f"{c.name}={c.value}")
    return "; ".join(pairs)


def _try_login(username: str, password: str, database_name: str) -> Tuple[str, Optional[str]]:
    login_url = f"{P6_BASE_URL}/login?DatabaseName={urllib.parse.quote(database_name)}"
    headers = {"username": username, "password": password, "Accept": P6_ACCEPT}
    if P6_VERSION:
        headers["Version"] = P6_VERSION
    r = requests.post(login_url, headers=headers, timeout=REQUEST_TIMEOUT, verify=False)
    if r.status_code >= 400:
        raise HTTPException(status_code=r.status_code, detail=f"Re-login failed: {r.text[:500]}")
    cookies = _extract_cookies(r)
    auth_token = r.headers.get("AuthToken") or r.headers.get("X-Auth-Token")
    if not auth_token and r.headers.get("content-type", "").startswith("application/json"):
        try:
            data = r.json()
            auth_token = data.get("AuthToken") or data.get("authToken") or data.get("token")
        except Exception:
            pass
    return cookies, auth_token


def _upstream_with_retry(ses_id: str, method: str, url: str,
                         headers: Dict[str, str],
                         data=None, json_body=None) -> requests.Response:
    """Perform request, if 401 and creds saved, re-login & retry once."""
    ses = SESSIONS.get(ses_id)
    if not ses:
        raise HTTPException(status_code=401, detail="Invalid or expired session_id. Please login again.")

    # Safety: only allow allowed host
    host = (url.split("//", 1)[-1]).split("/", 1)[0]
    if host != ALLOWED_HOST:
        raise HTTPException(status_code=400, detail=f"Host not allowed: {host}")

    # First attempt
    r = requests.request(method, url, headers=headers, data=data, json=json_body, timeout=REQUEST_TIMEOUT, verify=False)
    if r.status_code != 401:
        return r

    # 401 handling: retry once if we can re-login
    if ses.creds:
        try:
            new_cookies, new_token = _try_login(
                ses.creds.username, ses.creds.password, ses.creds.database_name
            )
            ses.cookies = new_cookies
            ses.auth_token = new_token
            # update headers & retry once
            headers = _default_headers(ses, extra={k: v for k, v in headers.items() if k not in ("Cookie", "AuthToken", "Accept", "Version")})
            r2 = requests.request(method, url, headers=headers, data=data, json=json_body, timeout=REQUEST_TIMEOUT, verify=False)
            return r2
        except HTTPException:
            # fall through to return the original 401
            pass

    return r


# ---------- Phase 3 helpers ----------
def _latest_session_id() -> Optional[str]:
    if not SESSIONS:
        return None
    # pick most recent by created_at
    return max(SESSIONS.items(), key=lambda kv: kv[1].created_at)[0]

def _json_or_text(resp: requests.Response):
    ctype = resp.headers.get("content-type", "")
    if ctype.startswith("application/json"):
        try:
            return resp.json()
        except Exception:
            return resp.text
    return resp.text


# ------------------------------
# Endpoints
# ------------------------------
@app.get("/health")
def health():
    session_list = []
    for sid, ses in SESSIONS.items():
        session_list.append({
            "session_id": sid,
            "created_at": datetime.utcfromtimestamp(ses.created_at).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "auto_login_enabled": ses.creds is not None
        })

    return {
        "ok": True,
        "time": int(time.time()),
        "base": P6_BASE_URL,
        "sessions": session_list
    }


@app.post("/login", response_model=LoginResponse)
def login(req: LoginRequest):
    cookies, auth_token = _try_login(req.username, req.password, req.databaseName)
    ses_id = _mk_session_id()
    SESSIONS[ses_id] = Session(
        cookies=cookies,
        auth_token=auth_token,
        database_name=req.databaseName,
        creds=SavedCreds(username=req.username, password=req.password, database_name=req.databaseName) if req.remember else None,
    )
    return LoginResponse(session_id=ses_id, cookies=cookies, authToken=auth_token, remember=req.remember)


@app.post("/call", response_model=ProxyResponse)
def call(req: CallRequest):
    ses = SESSIONS.get(req.session_id)
    if not ses:
        raise HTTPException(status_code=401, detail="Invalid or expired session_id. Please login again.")

    url = _build_target_url(req.path, req.query)
    headers = _default_headers(ses, req.headers or {})

    data = None
    json_body = None
    if req.body is not None:
        if isinstance(req.body, (dict, list)):
            json_body = req.body
        else:
            data = req.body

    r = _upstream_with_retry(req.session_id, req.method, url, headers, data, json_body)

    out_headers = {k: v for k, v in r.headers.items()}
    ctype = out_headers.get("content-type", "")
    body: Any
    if ctype.startswith("application/json"):
        try:
            body = r.json()
        except Exception:
            body = r.text
    else:
        body = r.text

    return ProxyResponse(status=r.status_code, headers=out_headers, body=body)


# ------------------------------
# Helper: OBS by name (exact match)
# ------------------------------
@app.get("/obs/byName", response_model=ProxyResponse)
def obs_by_name(session_id: str = Query(..., description="session_id from /login"),
                name: str = Query(..., description="Exact OBS Name"),
                fields: str = Query("CreateDate,CreateUser,Description,GUID,LastUpdateDate,LastUpdateUser,Name,ObjectId,ParentObjectId,SequenceNumber"),
                order_by: str = Query("", description="OrderBy expression (optional)")):
    ses = SESSIONS.get(session_id)
    if not ses:
        raise HTTPException(status_code=401, detail="Invalid or expired session_id. Please login again.")

    q = {
        "Filter": f"Name='{name}'",
        "Fields": fields,
        "OrderBy": order_by,
    }
    url = _build_target_url("/obs", q)
    headers = _default_headers(ses)

    r = _upstream_with_retry(session_id, "GET", url, headers)
    out_headers = {k: v for k, v in r.headers.items()}
    body = r.json() if out_headers.get("content-type", "").startswith("application/json") else r.text
    return ProxyResponse(status=r.status_code, headers=out_headers, body=body)


# ------------------------------
# Helper: Projects list
# ------------------------------
@app.get("/projects/list", response_model=ProxyResponse)
def projects_list(session_id: str = Query(...),
                  filter: Optional[str] = Query(None, description="P6 Filter expression"),
                  fields: str = Query("Id,Code,Name,StartDate,FinishDate,GUID,Status"),
                  order_by: str = Query("", description="OrderBy"),
                  limit: Optional[int] = Query(None, description="Optional limit via MaxObjects")):
    ses = SESSIONS.get(session_id)
    if not ses:
        raise HTTPException(status_code=401, detail="Invalid or expired session_id. Please login again.")

    q = {
        "Fields": fields,
        "OrderBy": order_by,
    }
    if filter:
        q["Filter"] = filter
    if limit:
        q["MaxObjects"] = limit

    url = _build_target_url("/project", q)
    headers = _default_headers(ses)

    r = _upstream_with_retry(session_id, "GET", url, headers)
    out_headers = {k: v for k, v in r.headers.items()}
    body = r.json() if out_headers.get("content-type", "").startswith("application/json") else r.text
    return ProxyResponse(status=r.status_code, headers=out_headers, body=body)


# ------------------------------
# Phase 3: Return only the latest session
# ------------------------------
@app.get("/session/active")
def session_active():
    sid = _latest_session_id()
    if not sid:
        raise HTTPException(status_code=404, detail="No active sessions")
    ses = SESSIONS[sid]
    return {
        "session_id": sid,
        "created_at": datetime.utcfromtimestamp(ses.created_at).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "auto_login_enabled": ses.creds is not None
    }


# ------------------------------
# Phase 3: OBS fuzzy find (Name LIKE %q%)
# ------------------------------
@app.get("/obs/find", response_model=ProxyResponse)
def obs_find(
    session_id: Optional[str] = Query(None, description="If omitted uses latest active session"),
    q: str = Query(..., description="Substring to search in OBS Name"),
    fields: str = Query("CreateDate,CreateUser,Description,GUID,LastUpdateDate,LastUpdateUser,Name,ObjectId,ParentObjectId,SequenceNumber"),
    order_by: str = Query("Name", description="OrderBy expression (optional)"),
    limit: Optional[int] = Query(50, description="Optional MaxObjects")
):
    sid = session_id or _latest_session_id()
    if not sid or sid not in SESSIONS:
        raise HTTPException(status_code=401, detail="No valid session. Login and try again.")

    ses = SESSIONS[sid]
    qparams = {
        "Filter": f"Name LIKE '%{q}%'",
        "Fields": fields,
        "OrderBy": order_by,
    }
    if limit:
        qparams["MaxObjects"] = limit

    url = _build_target_url("/obs", qparams)
    headers = _default_headers(ses)
    r = _upstream_with_retry(sid, "GET", url, headers)
    body = _json_or_text(r)
    return ProxyResponse(status=r.status_code, headers=dict(r.headers), body=body)


# ------------------------------
# Phase 3: Projects by OBS (by name or id)
# ------------------------------
@app.get("/projects/by_obs", response_model=ProxyResponse)
def projects_by_obs(
    session_id: Optional[str] = Query(None, description="If omitted uses latest active session"),
    obs_name: Optional[str] = Query(None, description="Exact OBS Name to resolve to ObjectId"),
    obs_id: Optional[str] = Query(None, description="OBS ObjectId (skips name lookup)"),
    fields: str = Query("Id,Code,Name,StartDate,FinishDate,GUID,Status,OBSObjectId"),
    order_by: str = Query("Name"),
    limit: Optional[int] = Query(100)
):
    sid = session_id or _latest_session_id()
    if not sid or sid not in SESSIONS:
        raise HTTPException(status_code=401, detail="No valid session. Login and try again.")
    ses = SESSIONS[sid]

    # Resolve OBS id if only name is provided
    oid = obs_id
    if not oid:
        if not obs_name:
            raise HTTPException(status_code=400, detail="Provide obs_name or obs_id")
        obs_q = {
            "Filter": f"Name='{obs_name}'",
            "Fields": "Name,ObjectId",
            "MaxObjects": 1,
        }
        obs_url = _build_target_url("/obs", obs_q)
        obs_headers = _default_headers(ses)
        obs_resp = _upstream_with_retry(sid, "GET", obs_url, obs_headers)
        obs_body = _json_or_text(obs_resp)
        if obs_resp.status_code >= 400:
            return ProxyResponse(status=obs_resp.status_code, headers=dict(obs_resp.headers), body=obs_body)
        try:
            items = obs_body if isinstance(obs_body, list) else json.loads(obs_body)
            if not items:
                raise HTTPException(status_code=404, detail=f"OBS '{obs_name}' not found")
            oid = items[0].get("ObjectId")
        except Exception:
            raise HTTPException(status=502, detail="Failed to parse OBS response")

    # Now pull projects that reference this OBS
    qparams = {
        "Fields": fields,
        "OrderBy": order_by,
        "Filter": f"OBSObjectId='{oid}'",
    }
    if limit:
        qparams["MaxObjects"] = limit

    proj_url = _build_target_url("/project", qparams)
    proj_headers = _default_headers(ses)
    proj_resp = _upstream_with_retry(sid, "GET", proj_url, proj_headers)
    body = _json_or_text(proj_resp)
    return ProxyResponse(status=proj_resp.status_code, headers=dict(proj_resp.headers), body=body)

# ==============================
# TOOL SCHEMA (Expanded)
# ==============================
TOOL_SCHEMA_JSON = r'''{
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "p6_login",
        "description": "Login to Oracle P6 and start a session. Set remember=true to enable auto-relogin.",
        "parameters": {
          "type": "object",
          "properties": {
            "username": {"type": "string"},
            "password": {"type": "string"},
            "databaseName": {"type": "string"},
            "remember": {"type": "boolean", "default": false}
          },
          "required": ["username", "password", "databaseName"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "p6_session_active",
        "description": "Return the latest active session (session_id).",
        "parameters": { "type": "object", "properties": {} }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "p6_obs_find",
        "description": "Fuzzy search OBS by name (LIKE %q%).",
        "parameters": {
          "type": "object",
          "properties": {
            "session_id": {"type": "string"},
            "q": {"type": "string"},
            "fields": {"type": "string", "default": "CreateDate,CreateUser,Description,GUID,LastUpdateDate,LastUpdateUser,Name,ObjectId,ParentObjectId,SequenceNumber"},
            "order_by": {"type": "string", "default": "Name"},
            "limit": {"type": "integer", "default": 50}
          },
          "required": ["q"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "p6_projects_by_obs",
        "description": "List projects that belong to a given OBS (by name or id).",
        "parameters": {
          "type": "object",
          "properties": {
            "session_id": {"type": "string"},
            "obs_name": {"type": "string"},
            "obs_id": {"type": "string"},
            "fields": {"type": "string", "default": "Id,Code,Name,StartDate,FinishDate,GUID,Status,OBSObjectId"},
            "order_by": {"type": "string", "default": "Name"},
            "limit": {"type": "integer", "default": 100}
          }
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "p6_call",
        "description": "Generic proxy call to P6 REST via MCP. Auto-relogin if remember=true was used at login.",
        "parameters": {
          "type": "object",
          "properties": {
            "session_id": {"type": "string"},
            "method": {"type": "string", "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"]},
            "path": {"type": "string"},
            "query": {"type": "object"},
            "headers": {"type": "object"},
            "body": {}
          },
          "required": ["session_id", "method", "path"]
        }
      }
    }
  ],
  "tool_server": {
    "base_url": "http://127.0.0.1:8080",
    "endpoints": {
      "p6_login": {"method": "POST", "path": "/login"},
      "p6_session_active": {"method": "GET", "path": "/session/active"},
      "p6_obs_find": {"method": "GET", "path": "/obs/find"},
      "p6_projects_by_obs": {"method": "GET", "path": "/projects/by_obs"},
      "p6_call":  {"method": "POST", "path": "/call"}
    }
  }
}'''

@app.get("/tool_schema.json")
def tool_schema():
    return json.loads(TOOL_SCHEMA_JSON)


@app.get("/.well-known/mcp.json")
def mcp_manifest():
    """
    MCP manifest endpoint for ChatGPT integration.
    This must be served at /.well-known/mcp.json for ChatGPT to discover the service.
    """
    return {
        "name": "primavera-p6-mcp-agent",
        "description": "Oracle Primavera P6 MCP Agent - REST API bridge for ChatGPT",
        "version": "0.3.0",
        "tools": [
            {
                "name": "p6_login",
                "description": "Login to Oracle P6 and start a session. Set remember=true to enable auto-relogin.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "username": {"type": "string"},
                        "password": {"type": "string"},
                        "databaseName": {"type": "string"},
                        "remember": {"type": "boolean", "default": False}
                    },
                    "required": ["username", "password", "databaseName"]
                }
            },
            {
                "name": "p6_session_active",
                "description": "Return the latest active session (session_id).",
                "inputSchema": {"type": "object", "properties": {}}
            },
            {
                "name": "p6_obs_find",
                "description": "Fuzzy search OBS by name (LIKE %q%).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string"},
                        "q": {"type": "string"},
                        "fields": {"type": "string", "default": "CreateDate,CreateUser,Description,GUID,LastUpdateDate,LastUpdateUser,Name,ObjectId,ParentObjectId,SequenceNumber"},
                        "order_by": {"type": "string", "default": "Name"},
                        "limit": {"type": "integer", "default": 50}
                    },
                    "required": ["q"]
                }
            },
            {
                "name": "p6_projects_by_obs",
                "description": "List projects that belong to a given OBS (by name or id).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string"},
                        "obs_name": {"type": "string"},
                        "obs_id": {"type": "string"},
                        "fields": {"type": "string", "default": "Id,Code,Name,StartDate,FinishDate,GUID,Status,OBSObjectId"},
                        "order_by": {"type": "string", "default": "Name"},
                        "limit": {"type": "integer", "default": 100}
                    }
                }
            },
            {
                "name": "p6_call",
                "description": "Generic proxy call to P6 REST via MCP. Auto-relogin if remember=true was used at login.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string"},
                        "method": {"type": "string", "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"]},
                        "path": {"type": "string"},
                        "query": {"type": "object"},
                        "headers": {"type": "object"},
                        "body": {}
                    },
                    "required": ["session_id", "method", "path"]
                }
            }
        ]
    }
