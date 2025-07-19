"""
Configuration management for MCP OAuth server.
"""
import os
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class Auth0Config:
    """Auth0 configuration settings."""
    domain: str
    client_id: str
    client_secret: str
    audience: Optional[str] = None

    def __post_init__(self):
        """Validate required configuration."""
        if not self.domain:
            raise ValueError("AUTH0_DOMAIN is required")
        if not self.client_id:
            raise ValueError("AUTH0_CLIENT_ID is required")
        if not self.client_secret:
            raise ValueError("AUTH0_CLIENT_SECRET is required")

    @property
    def authorize_url(self) -> str:
        """Auth0 authorization endpoint."""
        return f"https://{self.domain}/authorize"

    @property
    def token_url(self) -> str:
        """Auth0 token endpoint."""
        return f"https://{self.domain}/oauth/token"

    @property
    def userinfo_url(self) -> str:
        """Auth0 userinfo endpoint."""
        return f"https://{self.domain}/userinfo"

@dataclass
class MCPConfig:
    """MCP server configuration settings."""
    host: str = "localhost"
    port: int = 8000
    debug: bool = False
    issuer_url: Optional[str] = None

    def __post_init__(self):
        """Set default issuer URL if not provided."""
        if not self.issuer_url:
            self.issuer_url = f"http://{self.host}:{self.port}"

@dataclass
class AppConfig:
    """Main application configuration."""
    auth0: Auth0Config
    mcp: MCPConfig

    # OAuth settings
    default_scopes: list[str]
    required_scopes: list[str]

    # Security settings
    token_expiry_seconds: int = 3600
    enable_client_registration: bool = True

def load_config() -> AppConfig:
    """Load configuration from environment variables."""
    auth0_config = Auth0Config(
        domain=os.getenv("AUTH0_DOMAIN", ""),
        client_id=os.getenv("AUTH0_CLIENT_ID", ""),
        client_secret=os.getenv("AUTH0_CLIENT_SECRET", ""),
        audience=os.getenv("AUTH0_AUDIENCE")
    )

    mcp_config = MCPConfig(
        host=os.getenv("MCP_HOST", "localhost"),
        port=int(os.getenv("MCP_PORT", "8000")),
        debug=os.getenv("MCP_DEBUG", "false").lower() == "true",
        issuer_url=os.getenv("MCP_ISSUER_URL")
    )

    default_scopes = os.getenv("DEFAULT_SCOPES", "openid profile email").split()
    required_scopes = os.getenv("REQUIRED_SCOPES", "read:mcp").split()

    return AppConfig(
        auth0=auth0_config,
        mcp=mcp_config,
        default_scopes=default_scopes,
        required_scopes=required_scopes,
        token_expiry_seconds=int(os.getenv("TOKEN_EXPIRY_SECONDS", "3600")),
        enable_client_registration=os.getenv("ENABLE_CLIENT_REGISTRATION", "true").lower() == "true"
    )