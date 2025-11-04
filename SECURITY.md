# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.3.2   | :white_check_mark: |
| < 0.3.0 | :x:                |

## Security Features

### Built-in Security

The Primavera P6 MCP Agent includes several security features:

1. **API Key Protection**
   - Optional API key authentication via `MCP_API_KEY` environment variable
   - Custom header name via `MCP_API_KEY_HEADER` (default: `x-api-key`)

2. **CORS Configuration**
   - Configurable CORS origins via `CORS_ORIGINS` environment variable
   - Defaults to wildcard (`*`) for MCP compatibility
   - Automatically disables credentials with wildcard for security

3. **SSL/TLS Support**
   - Configurable SSL verification via `P6_VERIFY_SSL`
   - Recommended: Enable in production (`P6_VERIFY_SSL=true`)

4. **Host Allow Guard**
   - Restricts proxy calls to configured P6 server only
   - Prevents SSRF attacks via `ALLOWED_HOST` configuration

5. **Session Security**
   - Sessions stored locally in `session_store.json`
   - Credentials only saved when `remember=true` is explicitly set
   - Session lifecycle logging for audit trail

## Security Best Practices

### Production Deployment

1. **Enable SSL Verification**
   ```bash
   export P6_VERIFY_SSL=true
   ```

2. **Use API Key Protection**
   ```bash
   export MCP_API_KEY="your-strong-random-secret"
   export MCP_API_KEY_HEADER="x-api-key"
   ```

3. **Configure CORS Properly**
   ```bash
   # Only allow specific origins in production
   export CORS_ORIGINS="https://chatgpt.com,https://your-domain.com"
   ```

4. **Use HTTPS**
   - Deploy behind a reverse proxy (Nginx, Caddy) with SSL/TLS
   - Use Railway, Render, or other platforms with automatic HTTPS

5. **Protect Environment Variables**
   - Never commit `.env` files to version control
   - Use platform-specific secret management (Railway secrets, Azure Key Vault, etc.)
   - Rotate API keys regularly

### Session Storage

The `session_store.json` file contains:
- Session IDs and cookies
- Optional P6 credentials (only if `remember=true`)

**Recommendations:**
- Ensure file permissions are restricted (600 on Linux/Unix)
- Use Docker volumes for persistent storage
- Backup regularly but securely
- Consider encrypting the file at rest

### Logging

Session logging (`ENABLE_SESSION_LOGGING=true`) includes:
- Login attempts
- Session lifecycle events
- API call patterns

**Recommendations:**
- Review logs regularly for suspicious activity
- Use log aggregation tools (CloudWatch, Datadog, etc.)
- Set appropriate `LOG_LEVEL` (INFO for production, DEBUG only for troubleshooting)

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue:

1. **DO NOT** open a public GitHub issue
2. Create a private security advisory on GitHub or email the repository owner
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Fix Timeline**: Depends on severity
  - Critical: 1-7 days
  - High: 1-2 weeks
  - Medium: 2-4 weeks
  - Low: Next release cycle

## Known Security Considerations

### 1. Credential Storage
When `remember=true` is used, credentials are stored in plaintext in `session_store.json`.

**Mitigation**: 
- Only use `remember=true` in trusted environments
- Ensure proper file permissions and access controls
- Consider implementing credential encryption (future enhancement)

### 2. Session Persistence
Sessions persist across server restarts via JSON file storage.

**Mitigation**:
- Regular session cleanup
- Session expiry handling
- Monitor for session hijacking attempts

### 3. CORS Wildcard
Default CORS configuration allows all origins (`*`) for MCP compatibility.

**Mitigation**:
- Configure specific origins in production via `CORS_ORIGINS`
- Credentials are automatically disabled with wildcard
- Consider stricter CORS policy for sensitive deployments

### 4. P6 API Proxy
The `/call` endpoint proxies requests to P6 API.

**Mitigation**:
- Host allow guard restricts target hosts
- Session-based authentication required
- Consider rate limiting (future enhancement)

## Security Checklist for Production

- [ ] SSL/TLS enabled (`P6_VERIFY_SSL=true`)
- [ ] API key protection configured (`MCP_API_KEY` set)
- [ ] CORS origins restricted to specific domains
- [ ] Deployed behind HTTPS (reverse proxy or platform)
- [ ] Environment variables secured (not in git)
- [ ] Session store file permissions restricted
- [ ] Logging enabled and monitored
- [ ] Regular security updates applied
- [ ] Backup strategy for session store
- [ ] Incident response plan in place

## Dependency Security

We use standard Python packages with no known high-severity vulnerabilities:

- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `requests` - HTTP client
- `pydantic` - Data validation

**Recommendations**:
- Run `pip list --outdated` regularly
- Update dependencies with security fixes promptly
- Monitor GitHub security advisories

## Compliance Notes

### Data Protection
- No personally identifiable information (PII) is logged by default
- Credentials stored only when explicitly opted in (`remember=true`)
- Session data should be treated as sensitive

### Audit Trail
- Session lifecycle logging provides audit trail
- API call logging available for compliance
- Timestamps recorded for all operations

## Future Security Enhancements

Planned security improvements:

1. **Credential Encryption** - Encrypt stored credentials at rest
2. **Rate Limiting** - Prevent abuse and DoS attacks
3. **Request Signing** - HMAC signing for API requests
4. **Session Encryption** - Encrypt session data
5. **Audit Logging** - Enhanced audit trail
6. **Multi-factor Authentication** - Support for MFA
7. **IP Allowlisting** - Restrict access by IP address

## Resources

- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Python Security Best Practices](https://python.readthedocs.io/en/latest/library/security_warnings.html)

---

**Last Updated**: 2024-11-04  
**Version**: 0.3.2
