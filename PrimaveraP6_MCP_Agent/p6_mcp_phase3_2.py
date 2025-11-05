from __future__ import annotations
import os
import time
from datetime import datetime
import json
import urllib.parse
import logging
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

import requests
from fastapi import FastAPI, HTTPException, Query, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ==============================
# CONFIG HELPERS
# ==============================
def env_bool(key: str, default: str = "false") -> bool:
    return os.getenv(key, default).strip().lower() in {"true", "1", "yes", "y", "on"}


# ==============================
# CONFIG - Phase 3.2 Auto-Session Mode
# ==============================
P6_BASE_URL = os.getenv("P6_BASE_URL", "https://ca1.p6.oraclecloud.com/metrolinx/p6ws/restapi")
P6_ACCEPT = os.getenv("P6_ACCEPT", "application/json")
P6_VERSION = os.getenv("P6_VERSION", "")  # e.g., "23.12.0" if Oracle requires it
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "30"))
P6_VERIFY_SSL = env_bool("P6_VERIFY_SSL", "false")

# Phase 3.2 Configuration Flags
AUTO_SESSION_ENABLED = env_bool("AUTO_SESSION_ENABLED", "true")
AUTO_SESSION_STRICT_MODE = env_bool("AUTO_SESSION_STRICT_MODE", "true")
SESSION_STORE_FILE = os.getenv("SESSION_STORE_FILE", "session_store.json")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
ENABLE_SESSION_LOGGING = env_bool("ENABLE_SESSION_LOGGING", "true")

MCP_API_KEY = os.getenv("MCP_API_KEY")
MCP_API_KEY_HEADER = os.getenv("MCP_API_KEY_HEADER", "x-api-key")

ENABLE_TOOL_SCHEMA = env_bool("ENABLE_TOOL_SCHEMA", "true")
TOOL_SERVER_BASE_URL = os.getenv("TOOL_SERVER_BASE_URL", "https://primavera-p6-mcp-agent-production.up.railway.app")

DEFAULT_ALLOWED_HOST = (P6_BASE_URL.split("//", 1)[-1]).split("/", 1)[0]
ALLOWED_HOST = os.getenv("ALLOWED_HOST", DEFAULT_ALLOWED_HOST)

CORS_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "").split(",") if origin.strip()]
# For MCP compatibility, default to wildcard if no specific origins are set
if not CORS_ORIGINS:
    CORS_ORIGINS = ["*"]

if not logging.getLogger().handlers:
    logging.basicConfig(level=LOG_LEVEL)
else:
    logging.getLogger().setLevel(LOG_LEVEL)

logger = logging.getLogger("p6_mcp_agent")
logger.setLevel(LOG_LEVEL)


def session_log(level: int, message: str):
    if ENABLE_SESSION_LOGGING:
        logger.log(level, message)


if MCP_API_KEY:
    logger.info("API key protection enabled (header '%s').", MCP_API_KEY_HEADER)

if not P6_VERIFY_SSL and P6_BASE_URL.lower().startswith("https://"):
    logger.warning("SSL verification is disabled for P6 requests. Enable P6_VERIFY_SSL in production.")

if ENABLE_TOOL_SCHEMA:
    logger.info("Tool schema base URL set to %s", TOOL_SERVER_BASE_URL)
else:
    logger.info("Tool schema endpoint is disabled.")


def require_api_key(request: Request):
    if not MCP_API_KEY:
        return
    provided_key = request.headers.get(MCP_API_KEY_HEADER)
    if not provided_key or provided_key != MCP_API_KEY:
        logger.warning("Request blocked due to missing or invalid API key.")
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


api_dependencies: List[Any] = []
if MCP_API_KEY:
    api_dependencies.append(Depends(require_api_key))


# ==============================
# SESSION MANAGER - Phase 3.2
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


class SessionManager:
    """Phase 3.2: Hybrid session storage (in-memory + persistent JSON file)"""
    
    def __init__(self, store_file: str = SESSION_STORE_FILE):
        self.sessions: Dict[str, Session] = {}
        self.store_file = Path(store_file)
        self._load_from_disk()
    
    def _load_from_disk(self):
        """Load sessions from JSON file at startup"""
        if self.store_file.exists():
            try:
                with open(self.store_file, 'r') as f:
                    data = json.load(f)
                    for sid, sess_data in data.items():
                        self.sessions[sid] = Session(**sess_data)
                session_log(logging.INFO, f"Loaded {len(self.sessions)} session(s) from {self.store_file}")
            except Exception as e:
                logger.exception("Failed to load sessions from disk: %s", e)
    
    def _save_to_disk(self):
        """Save sessions to JSON file"""
        try:
            data = {sid: sess.dict() for sid, sess in self.sessions.items()}
            with open(self.store_file, 'w') as f:
                json.dump(data, f, indent=2)
            session_log(logging.DEBUG, f"Saved {len(self.sessions)} session(s) to {self.store_file}")
        except Exception as e:
            logger.exception("Failed to save sessions to disk: %s", e)
    
    def add_session(self, session_id: str, session: Session):
        """Add or update a session"""
        self.sessions[session_id] = session
        self._save_to_disk()
        session_log(logging.INFO, f"Session created: {session_id} (auto_login: {session.creds is not None})")
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID"""
        return self.sessions.get(session_id)
    
    def get_latest_session_id(self) -> Optional[str]:
        """Get the most recent session ID by creation time"""
        if not self.sessions:
            return None
        return max(self.sessions.items(), key=lambda kv: kv[1].created_at)[0]
    
    def get_latest_session(self) -> Optional[Tuple[str, Session]]:
        """Get the most recent session with its ID"""
        sid = self.get_latest_session_id()
        if sid:
            return sid, self.sessions[sid]
        return None
    
    def remove_session(self, session_id: str):
        """Remove a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            self._save_to_disk()
            session_log(logging.INFO, f"Session removed: {session_id}")
    
    def clear_all(self):
        """Clear all sessions"""
        self.sessions.clear()
        self._save_to_disk()
        session_log(logging.INFO, "All sessions cleared")
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all sessions with metadata"""
        result = []
        for sid, ses in self.sessions.items():
            result.append({
                "session_id": sid,
                "created_at": datetime.utcfromtimestamp(ses.created_at).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "auto_login_enabled": ses.creds is not None,
                "database": ses.database_name
            })
        return result


# Initialize global session manager
session_manager = SessionManager()


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
    session_id: Optional[str] = None  # Phase 3.2: Now optional with auto-session
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
app = FastAPI(
    title="P6 MCP Server",
    version="0.3.2 (Phase 3.2 - Auto Session)",
    dependencies=api_dependencies,
)

if CORS_ORIGINS:
    # Use allow_credentials=False with wildcard origins for security
    # (auth uses session_id in body, not cookies)
    allow_creds = False if "*" in CORS_ORIGINS else True
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=allow_creds,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info("CORS enabled for origins: %s (credentials: %s)", ", ".join(CORS_ORIGINS), allow_creds)

logger.info("Allowed upstream host: %s", ALLOWED_HOST)


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
    r = requests.post(login_url, headers=headers, timeout=REQUEST_TIMEOUT, verify=P6_VERIFY_SSL)
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
    ses = session_manager.get_session(ses_id)
    if not ses:
        raise HTTPException(status_code=401, detail="Invalid or expired session_id. Please login again.")

    # Safety: only allow allowed host
    host = (url.split("//", 1)[-1]).split("/", 1)[0]
    if host != ALLOWED_HOST:
        raise HTTPException(status_code=400, detail=f"Host not allowed: {host}")

    # First attempt
    r = requests.request(
        method,
        url,
        headers=headers,
        data=data,
        json=json_body,
        timeout=REQUEST_TIMEOUT,
        verify=P6_VERIFY_SSL,
    )
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
            headers = _default_headers(
                ses,
                extra={k: v for k, v in headers.items() if k not in ("Cookie", "AuthToken", "Accept", "Version")},
            )
            r2 = requests.request(
                method,
                url,
                headers=headers,
                data=data,
                json=json_body,
                timeout=REQUEST_TIMEOUT,
                verify=P6_VERIFY_SSL,
            )
            session_log(logging.INFO, f"Auto-relogin successful for session {ses_id}")
            return r2
        except HTTPException:
            # fall through to return the original 401
            pass

    return r


# ---------- Phase 3.2 Session Helper ----------
def _get_session_id_or_latest(provided_session_id: Optional[str]) -> str:
    """
    Phase 3.2: Auto-session injection logic
    - If session_id provided, use it
    - If not provided and AUTO_SESSION_ENABLED, use latest
    - If no session available and STRICT_MODE, raise 401
    """
    if provided_session_id:
        session_log(logging.DEBUG, f"Using provided session_id: {provided_session_id}")
        return provided_session_id
    
    if not AUTO_SESSION_ENABLED:
        raise HTTPException(
            status_code=401, 
            detail="session_id required (AUTO_SESSION_ENABLED is disabled)"
        )
    
    latest_sid = session_manager.get_latest_session_id()
    if not latest_sid:
        if AUTO_SESSION_STRICT_MODE:
            raise HTTPException(
                status_code=401,
                detail="No active session found. Please login first via /login"
            )
        else:
            raise HTTPException(status_code=401, detail="No sessions available")
    
    session_log(logging.DEBUG, f"Auto-injecting latest session: {latest_sid}")
    return latest_sid


# ---------- Phase 3 helpers ----------
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
@app.get("/")
def root():
    """Root endpoint with basic info and MCP discovery"""
    from fastapi import Response
    import json
    
    root_data = {
        "name": "Primavera P6 MCP Agent",
        "version": "0.3.2",
        "description": "Oracle Primavera P6 MCP Agent - REST API bridge for ChatGPT",
        "status": "online",
        "mcp_manifest": "/.well-known/mcp.json",
        "health_check": "/health",
        "documentation": "/docs",
        "auto_session_enabled": AUTO_SESSION_ENABLED
    }
    
    return Response(
        content=json.dumps(root_data, indent=2),
        media_type="application/json",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=300"
        }
    )


@app.get("/health")
def health():
    """Enhanced health check with MCP readiness status"""
    from fastapi import Response
    import json
    
    health_data = {
        "ok": True,
        "status": "healthy",
        "time": int(time.time()),
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "base": P6_BASE_URL,
        "auto_session_enabled": AUTO_SESSION_ENABLED,
        "auto_session_strict_mode": AUTO_SESSION_STRICT_MODE,
        "mcp_ready": True,
        "version": "0.3.2",
        "sessions": session_manager.list_sessions(),
        "endpoints": {
            "mcp_manifest": "/.well-known/mcp.json",
            "tool_schema": "/tool_schema.json",
            "login": "/login",
            "call": "/call",
            "obs_find": "/obs/find",
            "projects_by_obs": "/projects/by_obs"
        }
    }
    
    return Response(
        content=json.dumps(health_data, indent=2),
        media_type="application/json",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


@app.post("/login", response_model=LoginResponse)
def login(req: LoginRequest):
    cookies, auth_token = _try_login(req.username, req.password, req.databaseName)
    ses_id = _mk_session_id()
    session = Session(
        cookies=cookies,
        auth_token=auth_token,
        database_name=req.databaseName,
        creds=SavedCreds(username=req.username, password=req.password, database_name=req.databaseName) if req.remember else None,
    )
    session_manager.add_session(ses_id, session)
    return LoginResponse(session_id=ses_id, cookies=cookies, authToken=auth_token, remember=req.remember)


@app.post("/call", response_model=ProxyResponse)
def call(req: CallRequest):
    # Phase 3.2: Auto-inject session if not provided
    ses_id = _get_session_id_or_latest(req.session_id)
    ses = session_manager.get_session(ses_id)
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

    r = _upstream_with_retry(ses_id, req.method, url, headers, data, json_body)

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
def obs_by_name(session_id: Optional[str] = Query(None, description="session_id from /login (optional if auto-session enabled)"),
                name: str = Query(..., description="Exact OBS Name"),
                fields: str = Query("CreateDate,CreateUser,Description,GUID,LastUpdateDate,LastUpdateUser,Name,ObjectId,ParentObjectId,SequenceNumber"),
                order_by: str = Query("", description="OrderBy expression (optional)")):
    # Phase 3.2: Auto-inject session
    ses_id = _get_session_id_or_latest(session_id)
    ses = session_manager.get_session(ses_id)
    if not ses:
        raise HTTPException(status_code=401, detail="Invalid or expired session_id. Please login again.")

    q = {
        "Filter": f"Name='{name}'",
        "Fields": fields,
        "OrderBy": order_by,
    }
    url = _build_target_url("/obs", q)
    headers = _default_headers(ses)

    r = _upstream_with_retry(ses_id, "GET", url, headers)
    out_headers = {k: v for k, v in r.headers.items()}
    body = r.json() if out_headers.get("content-type", "").startswith("application/json") else r.text
    return ProxyResponse(status=r.status_code, headers=out_headers, body=body)


# ------------------------------
# Helper: Projects list
# ------------------------------
@app.get("/projects/list", response_model=ProxyResponse)
def projects_list(session_id: Optional[str] = Query(None, description="session_id (optional if auto-session enabled)"),
                  filter: Optional[str] = Query(None, description="P6 Filter expression"),
                  fields: str = Query("Id,Code,Name,StartDate,FinishDate,GUID,Status"),
                  order_by: str = Query("", description="OrderBy"),
                  limit: Optional[int] = Query(None, description="Optional limit via MaxObjects")):
    # Phase 3.2: Auto-inject session
    ses_id = _get_session_id_or_latest(session_id)
    ses = session_manager.get_session(ses_id)
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

    r = _upstream_with_retry(ses_id, "GET", url, headers)
    out_headers = {k: v for k, v in r.headers.items()}
    body = r.json() if out_headers.get("content-type", "").startswith("application/json") else r.text
    return ProxyResponse(status=r.status_code, headers=out_headers, body=body)


# ------------------------------
# Phase 3: Return only the latest session
# ------------------------------
@app.get("/session/active")
def session_active():
    latest = session_manager.get_latest_session()
    if not latest:
        raise HTTPException(status_code=404, detail="No active sessions")
    sid, ses = latest
    return {
        "session_id": sid,
        "created_at": datetime.utcfromtimestamp(ses.created_at).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "auto_login_enabled": ses.creds is not None,
        "database": ses.database_name
    }


# ------------------------------
# Phase 3.2: Session management endpoints
# ------------------------------
@app.delete("/session/{session_id}")
def delete_session(session_id: str):
    """Delete a specific session"""
    if session_id not in session_manager.sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    session_manager.remove_session(session_id)
    return {"message": f"Session {session_id} deleted"}


@app.delete("/sessions/clear")
def clear_all_sessions():
    """Clear all sessions"""
    session_manager.clear_all()
    return {"message": "All sessions cleared"}


# ------------------------------
# Phase 3: OBS fuzzy find (Name LIKE %q%)
# ------------------------------
@app.get("/obs/find", response_model=ProxyResponse)
def obs_find(
    session_id: Optional[str] = Query(None, description="session_id (optional if auto-session enabled)"),
    q: str = Query(..., description="Substring to search in OBS Name"),
    fields: str = Query("CreateDate,CreateUser,Description,GUID,LastUpdateDate,LastUpdateUser,Name,ObjectId,ParentObjectId,SequenceNumber"),
    order_by: str = Query("Name", description="OrderBy expression (optional)"),
    limit: Optional[int] = Query(50, description="Optional MaxObjects")
):
    # Phase 3.2: Auto-inject session
    sid = _get_session_id_or_latest(session_id)
    ses = session_manager.get_session(sid)
    if not ses:
        raise HTTPException(status_code=401, detail="No valid session. Login and try again.")

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
    session_id: Optional[str] = Query(None, description="session_id (optional if auto-session enabled)"),
    obs_name: Optional[str] = Query(None, description="Exact OBS Name to resolve to ObjectId"),
    obs_id: Optional[str] = Query(None, description="OBS ObjectId (skips name lookup)"),
    fields: str = Query("Id,Code,Name,StartDate,FinishDate,GUID,Status,OBSObjectId"),
    order_by: str = Query("Name"),
    limit: Optional[int] = Query(100)
):
    # Phase 3.2: Auto-inject session
    sid = _get_session_id_or_latest(session_id)
    ses = session_manager.get_session(sid)
    if not ses:
        raise HTTPException(status_code=401, detail="No valid session. Login and try again.")

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
def _build_tool_schema() -> Dict[str, Any]:
    base_url = TOOL_SERVER_BASE_URL.rstrip("/")
    return {
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
                            "remember": {"type": "boolean", "default": False},
                        },
                        "required": ["username", "password", "databaseName"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "p6_session_active",
                    "description": "Return the latest active session (session_id).",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "p6_obs_find",
                    "description": "Fuzzy search OBS by name (LIKE %q%). session_id is optional if auto-session is enabled.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string"},
                            "q": {"type": "string"},
                            "fields": {
                                "type": "string",
                                "default": "CreateDate,CreateUser,Description,GUID,LastUpdateDate,LastUpdateUser,Name,ObjectId,ParentObjectId,SequenceNumber",
                            },
                            "order_by": {"type": "string", "default": "Name"},
                            "limit": {"type": "integer", "default": 50},
                        },
                        "required": ["q"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "p6_projects_by_obs",
                    "description": "List projects that belong to a given OBS (by name or id). session_id is optional if auto-session is enabled.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string"},
                            "obs_name": {"type": "string"},
                            "obs_id": {"type": "string"},
                            "fields": {
                                "type": "string",
                                "default": "Id,Code,Name,StartDate,FinishDate,GUID,Status,OBSObjectId",
                            },
                            "order_by": {"type": "string", "default": "Name"},
                            "limit": {"type": "integer", "default": 100},
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "p6_call",
                    "description": "Generic proxy call to P6 REST via MCP. Auto-relogin if remember=true was used at login. session_id is optional if auto-session is enabled.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string"},
                            "method": {
                                "type": "string",
                                "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"],
                            },
                            "path": {"type": "string"},
                            "query": {"type": "object"},
                            "headers": {"type": "object"},
                            "body": {},
                        },
                        "required": ["method", "path"],
                    },
                },
            },
        ],
        "tool_server": {
            "base_url": base_url,
            "endpoints": {
                "p6_login": {"method": "POST", "path": "/login"},
                "p6_session_active": {"method": "GET", "path": "/session/active"},
                "p6_obs_find": {"method": "GET", "path": "/obs/find"},
                "p6_projects_by_obs": {"method": "GET", "path": "/projects/by_obs"},
                "p6_call": {"method": "POST", "path": "/call"},
            },
        },
    }


@app.get("/tool_schema.json")
def tool_schema():
    if not ENABLE_TOOL_SCHEMA:
        raise HTTPException(status_code=404, detail="Tool schema disabled")
    return _build_tool_schema()


@app.options("/.well-known/mcp.json")
def mcp_manifest_options():
    """Handle preflight requests for MCP manifest"""
    from fastapi import Response
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Max-Age": "3600"
        }
    )


@app.head("/.well-known/mcp.json")
def mcp_manifest_head():
    """Handle HEAD requests for MCP manifest (for connectivity checks)"""
    from fastapi import Response
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Content-Type": "application/json",
            "Cache-Control": "public, max-age=3600"
        }
    )


@app.get("/.well-known/mcp.json")
def mcp_manifest(request: Request):
    """
    MCP manifest endpoint for ChatGPT integration.
    This must be served at /.well-known/mcp.json for ChatGPT to discover the service.
    """
    base_url = TOOL_SERVER_BASE_URL.rstrip("/")
    
    # Build the manifest
    manifest = {
        "mcpVersion": "2024-11-05",
        "name": "primavera-p6-mcp-agent",
        "description": "Oracle Primavera P6 MCP Agent - REST API bridge for ChatGPT",
        "version": "0.3.2",
        "author": "Metrolinx P6 Team",
        "license": "MIT",
        "capabilities": {
            "tools": {},
            "resources": {},
            "prompts": {}
        },
        "tools": [
            {
                "name": "p6_login",
                "description": "Login to Oracle P6 and start a session. Set remember=true to enable auto-relogin.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "username": {"type": "string", "description": "P6 username"},
                        "password": {"type": "string", "description": "P6 password"},
                        "databaseName": {"type": "string", "description": "P6 database name"},
                        "remember": {"type": "boolean", "description": "Enable auto-relogin on session expiry", "default": False}
                    },
                    "required": ["username", "password", "databaseName"],
                    "additionalProperties": False
                }
            },
            {
                "name": "p6_session_active",
                "description": "Return the latest active session information.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False
                }
            },
            {
                "name": "p6_obs_find",
                "description": "Fuzzy search OBS (Organizational Breakdown Structure) by name. Auto-session enabled.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Optional session ID (auto-injected if not provided)"},
                        "q": {"type": "string", "description": "Search query for OBS name"},
                        "fields": {"type": "string", "description": "Comma-separated list of fields to return", "default": "CreateDate,CreateUser,Description,GUID,LastUpdateDate,LastUpdateUser,Name,ObjectId,ParentObjectId,SequenceNumber"},
                        "order_by": {"type": "string", "description": "Field to order results by", "default": "Name"},
                        "limit": {"type": "integer", "description": "Maximum number of results", "default": 50, "minimum": 1, "maximum": 1000}
                    },
                    "required": ["q"],
                    "additionalProperties": False
                }
            },
            {
                "name": "p6_projects_by_obs",
                "description": "List projects that belong to a given OBS (by name or id). Auto-session enabled.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Optional session ID (auto-injected if not provided)"},
                        "obs_name": {"type": "string", "description": "Exact OBS name to search for"},
                        "obs_id": {"type": "string", "description": "OBS Object ID (alternative to obs_name)"},
                        "fields": {"type": "string", "description": "Comma-separated list of fields to return", "default": "Id,Code,Name,StartDate,FinishDate,GUID,Status,OBSObjectId"},
                        "order_by": {"type": "string", "description": "Field to order results by", "default": "Name"},
                        "limit": {"type": "integer", "description": "Maximum number of results", "default": 100, "minimum": 1, "maximum": 1000}
                    },
                    "additionalProperties": False
                }
            },
            {
                "name": "p6_call",
                "description": "Generic proxy call to P6 REST API via MCP. Auto-relogin if remember=true was used at login. Auto-session enabled.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Optional session ID (auto-injected if not provided)"},
                        "method": {"type": "string", "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"], "description": "HTTP method"},
                        "path": {"type": "string", "description": "API path (e.g., '/projects', '/obs')"},
                        "query": {"type": "object", "description": "Query parameters as key-value pairs"},
                        "headers": {"type": "object", "description": "Additional HTTP headers"},
                        "body": {"description": "Request body for POST/PUT/PATCH requests"}
                    },
                    "required": ["method", "path"],
                    "additionalProperties": False
                }
            }
        ],
        "servers": [
            {
                "url": base_url,
                "description": "Primavera P6 MCP Agent Production Server"
            }
        ]
    }
    
    # Create response with proper headers for ChatGPT access
    from fastapi import Response
    import json
    
    response = Response(
        content=json.dumps(manifest, indent=2),
        media_type="application/json",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Cache-Control": "public, max-age=3600",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'"
        }
    )
    return response

