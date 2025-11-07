import json
import sys
from pathlib import Path
from typing import Dict

from starlette.requests import Request

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT / "PrimaveraP6_MCP_Agent"))

import p6_mcp_phase3_2 as p6


def _assert_manifest_headers(headers: Dict[str, str]) -> None:
    normalized = {k.lower(): v for k, v in headers.items()}
    for key, value in p6.MANIFEST_HEADERS.items():
        assert key.lower() in normalized
        assert normalized[key.lower()] == value


def test_health_endpoint_returns_status_payload_and_headers():
    response = p6.health()
    assert response.status_code == 200

    payload = json.loads(response.body.decode())
    assert payload["ok"] is True
    assert payload["status"] == "healthy"
    assert payload["mcp_ready"] is True
    assert payload["endpoints"]["mcp_manifest"] == "/.well-known/mcp.json"

    assert response.headers["Cache-Control"] == "no-cache, no-store, must-revalidate"
    assert response.headers["Pragma"] == "no-cache"
    assert response.headers["Expires"] == "0"


def test_manifest_endpoint_serves_json_with_expected_headers():
    request = Request({"type": "http", "headers": []})
    response = p6.mcp_manifest(request)
    assert response.status_code == 200

    manifest = json.loads(response.body.decode())
    assert manifest["schema_version"] == "1.0"
    assert manifest["name"] == "primavera-p6-mcp-agent"
    assert manifest["api"]["type"] == "rest"

    _assert_manifest_headers(response.headers)


def test_tool_schema_endpoint_available():
    schema = p6.tool_schema()
    assert "tools" in schema
    assert any(tool.get("function", {}).get("name") == "p6_login" for tool in schema["tools"])
    assert schema["tool_server"]["endpoints"]["p6_call"] == {"method": "POST", "path": "/call"}


def test_manifest_options_request_exposes_cors_headers():
    response = p6.mcp_manifest_options()
    assert response.status_code == 200

    headers = dict(response.headers)
    _assert_manifest_headers(headers)
    normalized = {k.lower(): v for k, v in headers.items()}
    assert normalized["access-control-max-age"] == "3600"


def test_manifest_head_request_returns_manifest_headers():
    response = p6.mcp_manifest_head()
    assert response.status_code == 200
    _assert_manifest_headers(dict(response.headers))