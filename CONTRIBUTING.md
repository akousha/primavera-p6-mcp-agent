# Contributing to Primavera P6 MCP Agent

Thank you for your interest in contributing to the Primavera P6 MCP Agent! This document provides guidelines for contributing to the project.

## Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/YOUR-USERNAME/primavera-p6-mcp-agent.git
   cd primavera-p6-mcp-agent
   ```

2. **Install Dependencies**
   ```bash
   cd PrimaveraP6_MCP_Agent
   pip install -r requirements.txt
   ```

3. **Run the Server**
   ```bash
   uvicorn p6_mcp_phase3_2:app --reload --port 8080
   ```

## Code Style

- Follow PEP 8 Python style guidelines
- Use type hints where appropriate
- Keep functions focused and well-documented
- Add docstrings to new functions and classes

## Making Changes

1. **Create a Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Your Changes**
   - Keep changes focused and atomic
   - Test your changes thoroughly
   - Update documentation as needed

3. **Test Locally**
   ```bash
   # Test the server starts correctly
   uvicorn p6_mcp_phase3_2:app --port 8080
   
   # Test the MCP manifest endpoint
   curl http://localhost:8080/.well-known/mcp.json
   
   # Test health check
   curl http://localhost:8080/health
   ```

4. **Commit Your Changes**
   ```bash
   git add .
   git commit -m "Brief description of changes"
   ```

5. **Push and Create PR**
   ```bash
   git push origin feature/your-feature-name
   ```
   Then create a Pull Request on GitHub.

## Pull Request Guidelines

- Provide a clear description of the changes
- Reference any related issues
- Ensure the PR description explains the "why" behind the changes
- Keep PRs focused on a single feature or fix
- Update documentation if you're adding/changing features

## Project Structure

```
primavera-p6-mcp-agent/
├── README.md                           # Main repository documentation
├── Dockerfile                          # Production Docker build
├── .gitignore                          # Git ignore rules
├── .dockerignore                       # Docker ignore rules
└── PrimaveraP6_MCP_Agent/              # Main application directory
    ├── p6_mcp_phase3_2.py             # Current production code
    ├── p6_mcp.py                       # Legacy version (for reference)
    ├── p6_mcp_phase3.1_backup.py      # Backup version
    ├── requirements.txt                # Python dependencies
    ├── Readme.md                       # Application README
    └── PrimaveraP6_MCP_Agent/          # Additional documentation
        ├── README.md                   # Detailed feature docs
        ├── DEPLOYMENT.md              # Deployment guides
        ├── PROJECT_SUMMARY.md         # Project overview
        ├── .env.example               # Environment template
        ├── docker-compose.yml         # Multi-service setup
        └── nginx.conf                 # Nginx configuration
```

## Areas for Contribution

### High Priority
- Additional API endpoints (activities, WBS, resources)
- Enhanced error handling and logging
- Performance optimizations
- Security improvements

### Medium Priority
- Unit and integration tests
- API documentation improvements
- Additional deployment examples
- Response caching

### Nice to Have
- UI dashboard
- Webhook support
- Multi-tenant support
- Advanced analytics

## Environment Variables

When adding new configuration options:
1. Add to `.env.example` with documentation
2. Add to README.md configuration section
3. Use reasonable defaults
4. Document in code comments

## Testing

While we don't have automated tests yet, please manually test:
- The MCP manifest endpoint (`/.well-known/mcp.json`)
- All modified endpoints
- Error cases and edge conditions
- CORS headers if modifying CORS configuration

## Documentation

Update documentation when:
- Adding new features or endpoints
- Changing configuration options
- Modifying deployment procedures
- Fixing bugs that affect usage

## Questions?

Feel free to open an issue for:
- Questions about the codebase
- Suggestions for improvements
- Bug reports
- Feature requests

## Code of Conduct

- Be respectful and constructive
- Welcome newcomers and help them get started
- Focus on the best solution, not winning arguments
- Assume good intentions

Thank you for contributing! 🎉
