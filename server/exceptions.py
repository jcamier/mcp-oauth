"""
Custom exceptions for MCP OAuth server.
"""

class MCPOAuthError(Exception):
    """Base exception for MCP OAuth errors."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class Auth0Error(MCPOAuthError):
    """Auth0 specific errors."""
    pass

class TokenValidationError(MCPOAuthError):
    """Token validation errors."""

    def __init__(self, message: str):
        super().__init__(message, status_code=401)

class AuthorizationError(MCPOAuthError):
    """Authorization errors."""

    def __init__(self, message: str):
        super().__init__(message, status_code=403)

class ConfigurationError(MCPOAuthError):
    """Configuration errors."""

    def __init__(self, message: str):
        super().__init__(message, status_code=500)

class ClientRegistrationError(MCPOAuthError):
    """Client registration errors."""

    def __init__(self, message: str):
        super().__init__(message, status_code=400)