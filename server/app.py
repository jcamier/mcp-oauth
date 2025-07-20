"""
Main FastMCP server application with Auth0 OAuth authentication.

This module sets up a FastMCP server with OAuth authentication using Auth0,
demonstrating a clean modular architecture.
"""

import logging
import uvicorn
from typing import Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from fastmcp import FastMCP
from fastmcp.server.auth.auth import ClientRegistrationOptions

from server.config import load_config, AppConfig
from server.oauth import Auth0OAuthProvider
from server.exceptions import MCPOAuthError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting MCP OAuth server...")
    yield
    logger.info("Shutting down MCP OAuth server...")


def create_oauth_provider(config: AppConfig) -> Auth0OAuthProvider:
    """
    Create and configure the Auth0 OAuth provider.

    Args:
        config: Application configuration

    Returns:
        Configured Auth0OAuthProvider instance
    """
    client_registration_options = ClientRegistrationOptions(
        enabled=config.enable_client_registration,
        valid_scopes=config.default_scopes + config.required_scopes,
        default_scopes=config.default_scopes,
    ) if config.enable_client_registration else None

    return Auth0OAuthProvider(
        auth0_config=config.auth0,
        mcp_issuer_url=config.mcp.issuer_url,
        client_registration_options=client_registration_options,
        required_scopes=config.required_scopes,
        token_expiry_seconds=config.token_expiry_seconds,
    )


def create_mcp_server(oauth_provider: Auth0OAuthProvider) -> FastMCP:
    """
    Create and configure the FastMCP server with tools.

    Args:
        oauth_provider: Configured OAuth provider

    Returns:
        Configured FastMCP server
    """
    # Initialize FastMCP server with OAuth
    mcp = FastMCP("Secure MCP Server", auth=oauth_provider)

    # Add your MCP tools here
    @mcp.tool()
    def get_weather(city: str) -> Dict[str, Any]:
        """
        Get weather information for a city.

        Args:
            city: Name of the city

        Returns:
            Mock weather data
        """
        logger.info(f"Getting weather for {city}")
        return {
            "city": city,
            "temperature": "22°C",
            "condition": "Sunny",
            "humidity": "60%",
            "message": f"Weather data for {city} (demo)"
        }

    @mcp.tool()
    def get_user_info() -> Dict[str, Any]:
        """
        Get current authenticated user information.

        Returns:
            User information from OAuth token
        """
        # This would typically access the current user context
        # For now, return a placeholder
        logger.info("Getting user info")
        return {
            "message": "User authenticated successfully",
            "note": "In a real implementation, this would return actual user data from the OAuth token"
        }

    @mcp.tool()
    def protected_action(action: str) -> Dict[str, Any]:
        """
        Perform a protected action that requires authentication.

        Args:
            action: Action to perform

        Returns:
            Result of the action
        """
        logger.info(f"Performing protected action: {action}")
        return {
            "action": action,
            "status": "completed",
            "message": f"Successfully performed: {action}",
            "authenticated": True
        }

    return mcp


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application
    """
    # Load configuration
    try:
        config = load_config()
        logger.info(f"Configuration loaded successfully for Auth0 domain: {config.auth0.domain}")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise

    # Create OAuth provider
    oauth_provider = create_oauth_provider(config)

    # Create MCP server
    mcp_server = create_mcp_server(oauth_provider)

    # Create FastAPI app
    app = FastAPI(
        title="Secure MCP Server",
        description="FastMCP server with Auth0 OAuth authentication",
        version="1.0.0",
        lifespan=lifespan
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global exception handler for OAuth errors
    @app.exception_handler(MCPOAuthError)
    async def oauth_exception_handler(request: Request, exc: MCPOAuthError):
        """Handle OAuth-related exceptions."""
        logger.error(f"OAuth error: {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "oauth_error",
                "message": exc.message,
                "status_code": exc.status_code
            }
        )

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "service": "MCP OAuth Server"}

    # Debug endpoint (remove in production)
    @app.get("/debug/auth0")
    async def debug_auth0():
        """Debug endpoint to check Auth0 configuration."""
        try:
            credentials = await oauth_provider.get_client_credentials()
            return {
                "auth0_configured": True,
                "domain": credentials["domain"],
                "client_id": credentials["client_id"],
                "audience": credentials["audience"],
            }
        except Exception as e:
            logger.error(f"Debug endpoint error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # Auth0 callback endpoint
    @app.get("/auth0/callback")
    async def auth0_callback(request: Request):
        """Handle Auth0 OAuth callback."""
        return await oauth_provider.handle_auth0_callback(request)

    # OAuth discovery endpoint
    @app.get("/.well-known/oauth-authorization-server")
    async def oauth_metadata():
        """OAuth authorization server metadata endpoint."""
        auth0_base = f"https://{config.auth0.domain}"
        return {
            "issuer": auth0_base,
            "authorization_endpoint": f"{auth0_base}/authorize",
            "token_endpoint": f"{auth0_base}/oauth/token",
            "registration_endpoint": f"{auth0_base}/oidc/register" if config.enable_client_registration else None,
            "scopes_supported": config.default_scopes + config.required_scopes,
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code"],
            "code_challenge_methods_supported": ["S256"],
        }

    # Mount MCP server
    mcp_app = mcp_server.http_app(path="/mcp")
    app.mount("/mcp", mcp_app)

    logger.info("FastAPI application created successfully")
    return app


# Create the application instance
app = create_app()


def main():
    """Run the application."""
    try:
        config = load_config()
        logger.info(f"Starting server on {config.mcp.host}:{config.mcp.port}")

        uvicorn.run(
            "server.app:app",
            host=config.mcp.host,
            port=config.mcp.port,
            reload=config.mcp.debug,
            log_level="info" if not config.mcp.debug else "debug"
        )
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise


if __name__ == "__main__":
    main()