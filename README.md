# FastMCP OAuth Server with Auth0

A modular FastMCP server implementation with Auth0 OAuth 2.0 authentication

## Features

- 🔐 **OAuth 2.0 Authentication** with Auth0
- 🛠️ **FastMCP Integration** for AI tool serving
- 🔍 **Debugging Support** with health checks
- 📊 **Structured Logging** throughout the application

## Project Structure

```
mcp-oauth/
├── server/              # FastMCP server (OAuth-secured)
│   ├── app.py          # Main server application
│   ├── oauth.py        # Auth0 OAuth provider
│   ├── config.py       # Configuration management
│   └── exceptions.py   # Custom exceptions
├── client/              # MCP client (OAuth-enabled)
│   ├── client.py       # Main client implementation
│   ├── auth_handler.py # OAuth authentication handler
│   └── cli.py         # Command-line interface
├── demos/               # Usage demonstrations
│   ├── basic_demo.py   # Complete OAuth flow demo
│   └── weather_demo.py # Weather tool demo
├── pyproject.toml       # Project configuration and dependencies
├── .env                # Environment variables (create from template below)
└── README.md           # This file
```

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate  # On macOS/Linux
# .venv\Scripts\activate   # On Windows

# Install dependencies
uv sync
```

### 2. Configure Auth0

1. **Create Auth0 Application:**
   - Go to [Auth0 Dashboard](https://manage.auth0.com/) → Applications
   - Click "Create Application"
   - Create a Name and choose "Regular Web Application"
   - Note down: Domain, Client ID, Client Secret from your Settings tab

2. **Configure Callback URLs:**
   ```
   http://localhost:8000/auth0/callback
   ```

3. **Configure Logout URLs:**
   ```
   http://localhost:8000
   ```

4. **Create API (Optional):**
   - Go to APIs → Create API
   - Set identifier (e.g., `https://mcp-server.example.com`)
   - This becomes your `AUTH0_AUDIENCE`

### 3. Environment Variables

Create a `.env` file in the project root using `.env.example` as a template:

```bash
# Auth0 Configuration (Required)
AUTH0_DOMAIN=your-tenant.auth0.com
AUTH0_CLIENT_ID=your_auth0_client_id_here
AUTH0_CLIENT_SECRET=your_auth0_client_secret_here
AUTH0_AUDIENCE=your_api_identifier_here

# MCP Server Configuration
MCP_HOST=localhost
MCP_PORT=8000
MCP_DEBUG=false
MCP_ISSUER_URL=http://localhost:8000

# OAuth Scopes Configuration
DEFAULT_SCOPES=openid profile email
REQUIRED_SCOPES=read:mcp write:mcp

# Security Settings
TOKEN_EXPIRY_SECONDS=3600
ENABLE_CLIENT_REGISTRATION=true
```

### 4. Run the Server

```bash
uv run python server/app.py
# Or use the script entry point:
uv run mcp-server
```

The server will start on `http://localhost:8000`

### 5. Test with the Client

**Interactive CLI:**
```bash
uv run python client/cli.py
# Or use the script entry point:
uv run mcp-client
```

**Run Demos:**
```bash
# Basic OAuth flow demo
uv run python demos/basic_demo.py
# Or: uv run mcp-demo

# Weather tool demo
uv run python demos/weather_demo.py
```

## Architecture Overview

### Modular Design

This project demonstrates clean separation of concerns:

#### `config.py` - Configuration Management
- **`Auth0Config`**: Auth0-specific settings with validation
- **`MCPConfig`**: MCP server configuration
- **`AppConfig`**: Combined application configuration
- **`load_config()`**: Environment variable loading with defaults

#### `oauth.py` - OAuth Provider
- **`Auth0OAuthProvider`**: Complete OAuth 2.0 implementation
- Handles authorization flows, token exchange, and validation
- Integrates with Auth0 APIs
- Manages client registration and scopes

#### `exceptions.py` - Error Handling
- **`MCPOAuthError`**: Base exception class
- **`Auth0Error`**: Auth0-specific errors
- **`TokenValidationError`**: Token-related errors
- **`AuthorizationError`**: Authorization failures

#### `app.py` - Main Application
- **`create_oauth_provider()`**: OAuth provider factory
- **`create_mcp_server()`**: MCP server with tools
- **`create_app()`**: FastAPI application setup
- Route handlers and middleware configuration

## API Endpoints

### OAuth Endpoints
- `GET /.well-known/oauth-authorization-server` - OAuth discovery
- `GET /auth0/callback` - Auth0 callback handler

### MCP Endpoints
- `POST /mcp` - MCP protocol endpoint (requires authentication)

### Utility Endpoints
- `GET /health` - Health check
- `GET /debug/auth0` - Auth0 configuration debug (development only)

## MCP Tools

The server includes example tools that require authentication:

### `get_weather(city: str)`
Mock weather data for a given city.

### `get_user_info()`
Returns current authenticated user information.

### `protected_action(action: str)`
Demonstrates a protected action requiring authentication.

## Usage Examples

### Testing with MCP Inspector

```bash
# Install MCP Inspector
npm install -g @modelcontextprotocol/inspector

# Test the server
npx @modelcontextprotocol/inspector http://localhost:8000/mcp
```

### Testing with cURL

```bash
# Health check
curl http://localhost:8000/health

# Debug Auth0 configuration
curl http://localhost:8000/debug/auth0

# OAuth discovery
curl http://localhost:8000/.well-known/oauth-authorization-server
```

## Development

### Code Quality

The project follows Python best practices:

- **Type hints** throughout the codebase
- **Docstrings** for all classes and functions
- **Structured logging** with appropriate levels
- **Error handling** with custom exceptions
- **Configuration validation** with clear error messages

### Testing

```bash
# Install development dependencies
uv sync --extra dev

# Run tests (when implemented)
uv run pytest tests/
```

### Code Formatting

```bash
# Format code
uv run black .

# Sort imports
uv run isort .

# Lint with ruff
uv run ruff check .
uv run ruff format .
```

## Production Considerations

### Security

1. **Environment Variables**: Never commit `.env` files
2. **CORS Configuration**: Restrict `allow_origins` in production
3. **Token Storage**: Replace in-memory storage with Redis/database
4. **HTTPS**: Always use HTTPS in production
5. **Secrets Management**: Use proper secret management systems

### Scaling

1. **Database**: Replace in-memory storage with persistent storage
2. **Caching**: Add Redis for token caching
3. **Load Balancing**: Configure for multiple instances
4. **Monitoring**: Add application monitoring and metrics

### Configuration

Update the following for production:

```python
# In app.py - CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Restrict origins
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Restrict methods
    allow_headers=["Authorization", "Content-Type"],  # Restrict headers
)
```

## Troubleshooting

### Common Issues

1. **Auth0 Configuration Errors**
   - Verify callback URLs match exactly
   - Check Auth0 domain format (no `https://`)
   - Ensure client secret is correct

2. **Token Validation Failures**
   - Check token expiration
   - Verify required scopes are granted
   - Ensure proper audience configuration

3. **CORS Issues**
   - Update CORS configuration for your client domain
   - Check preflight request handling

### Debug Mode

Enable debug mode for detailed logging:

```bash
MCP_DEBUG=true uv run python server/app.py
```

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Follow the existing code style
4. Add tests for new functionality
5. Submit a pull request

## Support

For issues and questions:
- Check the [FastMCP documentation](https://github.com/jlowin/fastmcp)
- Review [Auth0 documentation](https://auth0.com/docs)
- Open an issue in this repository