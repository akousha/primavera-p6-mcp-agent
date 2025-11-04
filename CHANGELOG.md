# Changelog

All notable changes to the Primavera P6 MCP Agent will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.2] - 2025-11-03

### Added
- MCP manifest endpoint at `/.well-known/mcp.json` for ChatGPT integration
- CORS middleware with wildcard default for MCP compatibility
- Automatic CORS credentials disabling with wildcard origins for security
- Comprehensive documentation (README, CONTRIBUTING, SECURITY, LICENSE)
- .dockerignore for optimized Docker builds
- Enhanced .gitignore for Python projects

### Changed
- Switched from `p6_mcp.py` to `p6_mcp_phase3_2.py` as production version
- Updated Dockerfile to use `p6_mcp_phase3_2:app`
- Improved CORS configuration with environment variable support
- CORS_ORIGINS now defaults to `["*"]` if not set (MCP compatibility)

### Fixed
- CORS allow_credentials set to False with wildcard origins (security fix)
- MCP manifest includes all 5 tools with proper schemas

### Security
- API key protection via `MCP_API_KEY` environment variable
- Host allow guard to prevent SSRF attacks
- Configurable SSL verification for production/development
- Session-based authentication with lifecycle logging

## [0.3.1] - 2025-10-24

### Added
- Advanced session management with JSON persistence
- Auto-reconnection on session expiry
- Session lifecycle logging
- Configurable session store file location

### Changed
- Enhanced configuration via environment variables
- Improved error handling and retry logic

## [0.3.0] - 2025-10-24

### Added
- Auto-session mode with automatic session ID injection
- Strict mode for session validation
- Health check endpoint with session status
- Tool schema endpoint for ChatGPT integration
- OBS fuzzy search endpoint (`/obs/find`)
- Projects by OBS endpoint (`/projects/by_obs`)

### Changed
- Refactored session management into SessionManager class
- Improved logging configuration
- Enhanced security features

## [0.2.0] - 2025-10-24

### Added
- Generic `/call` endpoint for P6 API proxy
- Session persistence across server restarts
- Optional credential storage with `remember` flag
- SSL verification configuration

### Changed
- Improved error handling
- Enhanced request timeout handling

## [0.1.0] - 2025-10-24

### Added
- Initial release
- Basic `/login` endpoint for P6 authentication
- FastAPI-based MCP server
- Docker containerization support
- Basic CORS support
- Environment-based configuration

### Security
- Basic session management
- Cookie-based authentication

---

## Legend

- `Added` - New features
- `Changed` - Changes in existing functionality
- `Deprecated` - Soon-to-be removed features
- `Removed` - Removed features
- `Fixed` - Bug fixes
- `Security` - Security improvements

## Links

- [Repository](https://github.com/akousha/primavera-p6-mcp-agent)
- [Production Deployment](https://primavera-p6-mcp-agent-production.up.railway.app)
- [MCP Manifest](https://primavera-p6-mcp-agent-production.up.railway.app/.well-known/mcp.json)
