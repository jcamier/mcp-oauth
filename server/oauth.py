"""
Auth0 OAuth provider for FastMCP servers.

This module provides a complete OAuth 2.0 implementation for Auth0,
compatible with the FastMCP authentication framework.
"""

import time
import logging
from typing import Dict, Optional, List
from secrets import token_hex, token_urlsafe
from urllib.parse import urlencode, quote_plus

import httpx
from fastmcp.server.auth.auth import OAuthProvider, ClientRegistrationOptions
from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    RefreshToken,
    construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from pydantic import AnyHttpUrl
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import RedirectResponse, JSONResponse

from .config import Auth0Config
from .exceptions import (
    Auth0Error,
    TokenValidationError,
    AuthorizationError,
)

logger = logging.getLogger(__name__)


class Auth0OAuthProvider(OAuthProvider):
    """
    Auth0 OAuth 2.0 provider for FastMCP servers.

    This provider handles the complete OAuth flow with Auth0, including:
    - Authorization code exchange
    - Token validation and management
    - Client registration
    - Scope validation
    """

    def __init__(
        self,
        auth0_config: Auth0Config,
        mcp_issuer_url: str,
        client_registration_options: Optional[ClientRegistrationOptions] = None,
        required_scopes: Optional[List[str]] = None,
        token_expiry_seconds: int = 3600,
    ):
        """
        Initialize the Auth0 OAuth provider.

        Args:
            auth0_config: Auth0 configuration object
            mcp_issuer_url: URL of the MCP server
            client_registration_options: Client registration settings
            required_scopes: Required OAuth scopes
            token_expiry_seconds: Token expiration time in seconds
        """
        super().__init__(
            issuer_url=mcp_issuer_url,
            client_registration_options=client_registration_options,
            required_scopes=required_scopes,
        )

        self.auth0_config = auth0_config
        self.mcp_issuer_url = mcp_issuer_url
        self.token_expiry_seconds = token_expiry_seconds

        # In-memory storage (use Redis/database in production)
        self.auth_codes: Dict[str, AuthorizationCode] = {}
        self.tokens: Dict[str, AccessToken] = {}
        self.state_mapping: Dict[str, Dict[str, str]] = {}
        self.clients: Dict[str, OAuthClientInformationFull] = {}

        logger.info(f"Auth0 OAuth provider initialized for domain: {auth0_config.domain}")

    async def get_client(self, client_id: str) -> Optional[OAuthClientInformationFull]:
        """Retrieve an OAuth client by its ID."""
        return self.clients.get(client_id)

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        """Register a new OAuth client."""
        logger.info(f"Registering new OAuth client: {client_info.client_id}")
        self.clients[client_info.client_id] = client_info

    async def authorize(
        self,
        client: OAuthClientInformationFull,
        params: AuthorizationParams
    ) -> str:
        """
        Generate an authorization URL for Auth0 OAuth flow.

        Args:
            client: OAuth client information
            params: Authorization parameters

        Returns:
            Auth0 authorization URL
        """
        try:
            state = params.state or token_urlsafe(32)

            # Store state mapping for callback handling
            self.state_mapping[state] = {
                "client_id": client.client_id,
                "code_challenge": params.code_challenge or "",
                "redirect_uri_provided_explicitly": str(params.redirect_uri_provided_explicitly),
                "redirect_uri": str(params.redirect_uri),
            }

            # Build Auth0 authorization parameters
            auth_params = {
                "client_id": self.auth0_config.client_id,
                "redirect_uri": f"{self.mcp_issuer_url}/auth0/callback",
                "response_type": "code",
                "state": state,
                "scope": " ".join(params.scopes or ["openid", "profile", "email"]),
            }

            # Add audience if configured
            if self.auth0_config.audience:
                auth_params["audience"] = self.auth0_config.audience

            # Add PKCE challenge if provided
            if params.code_challenge:
                auth_params["code_challenge"] = params.code_challenge
                auth_params["code_challenge_method"] = "S256"

            auth_url = construct_redirect_uri(self.auth0_config.authorize_url, **auth_params)

            logger.info(f"Generated authorization URL for client {client.client_id}")
            return auth_url

        except Exception as e:
            logger.error(f"Failed to generate authorization URL: {e}")
            raise AuthorizationError(f"Failed to generate authorization URL: {e}")

    async def load_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: str
    ) -> Optional[AuthorizationCode]:
        """Retrieve an authorization code."""
        code = self.auth_codes.get(authorization_code)
        if code and code.client_id == client.client_id:
            return code
        return None

    async def exchange_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: AuthorizationCode
    ) -> OAuthToken:
        """
        Exchange an authorization code for tokens with Auth0.

        Args:
            client: OAuth client information
            authorization_code: Authorization code to exchange

        Returns:
            OAuth token response
        """
        try:
            if authorization_code.code not in self.auth_codes:
                raise TokenValidationError("Invalid authorization code")

            # Exchange code for tokens with Auth0
            token_data = await self._exchange_code_with_auth0(authorization_code)

            # Generate MCP access token
            mcp_token = f"mcp_{token_hex(32)}"

            # Store access token
            self.tokens[mcp_token] = AccessToken(
                token=mcp_token,
                client_id=client.client_id,
                scopes=authorization_code.scopes,
                expires_at=int(time.time()) + self.token_expiry_seconds,
            )

            # Clean up authorization code
            del self.auth_codes[authorization_code.code]

            logger.info(f"Successfully exchanged authorization code for client {client.client_id}")

            return OAuthToken(
                access_token=mcp_token,
                token_type="Bearer",
                expires_in=self.token_expiry_seconds,
                scope=" ".join(authorization_code.scopes),
                refresh_token=token_data.get("refresh_token"),
            )

        except Exception as e:
            logger.error(f"Failed to exchange authorization code: {e}")
            if isinstance(e, (TokenValidationError, Auth0Error)):
                raise
            raise Auth0Error(f"Token exchange failed: {e}")

    async def _exchange_code_with_auth0(self, auth_code: AuthorizationCode) -> Dict:
        """Exchange authorization code with Auth0."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.auth0_config.token_url,
                data={
                    "grant_type": "authorization_code",
                    "client_id": self.auth0_config.client_id,
                    "client_secret": self.auth0_config.client_secret,
                    "code": auth_code.code,
                    "redirect_uri": f"{self.mcp_issuer_url}/auth0/callback",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            if response.status_code != 200:
                error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                error_msg = error_data.get("error_description", "Token exchange failed")
                raise Auth0Error(f"Auth0 token exchange failed: {error_msg}")

            return response.json()

    async def load_access_token(self, token: str) -> Optional[AccessToken]:
        """
        Load and validate an access token.

        Args:
            token: Access token to validate

        Returns:
            AccessToken object if valid, None otherwise
        """
        access_token = self.tokens.get(token)
        if not access_token:
            return None

        # Check if token is expired
        if access_token.expires_at and access_token.expires_at < time.time():
            logger.info(f"Token expired for client {access_token.client_id}")
            del self.tokens[token]
            return None

        return access_token

    async def revoke_token(self, token) -> None:
        """Revoke a token."""
        if hasattr(token, 'token') and token.token in self.tokens:
            logger.info(f"Revoking token for client {token.client_id}")
            del self.tokens[token.token]

    async def load_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: str
    ) -> Optional[RefreshToken]:
        """Load refresh token (not implemented in this example)."""
        raise NotImplementedError("Refresh token handling not implemented")

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: List[str]
    ) -> OAuthToken:
        """Exchange refresh token (not implemented in this example)."""
        raise NotImplementedError("Refresh token exchange not implemented")

    async def handle_auth0_callback(self, request: Request) -> RedirectResponse:
        """
        Handle Auth0 OAuth callback.

        Args:
            request: Starlette request object

        Returns:
            Redirect response to the original client
        """
        try:
            code = request.query_params.get("code")
            state = request.query_params.get("state")
            error = request.query_params.get("error")

            if error:
                error_description = request.query_params.get("error_description", "Unknown error")
                logger.error(f"Auth0 callback error: {error} - {error_description}")
                raise Auth0Error(f"Auth0 error: {error_description}")

            if not code or not state:
                raise Auth0Error("Missing code or state parameter")

            # Retrieve state mapping
            state_data = self.state_mapping.get(state)
            if not state_data:
                raise Auth0Error("Invalid state parameter")

            # Create MCP authorization code
            mcp_code = f"mcp_{token_hex(16)}"
            auth_code = AuthorizationCode(
                code=mcp_code,
                client_id=state_data["client_id"],
                redirect_uri=AnyHttpUrl(state_data["redirect_uri"]),
                redirect_uri_provided_explicitly=state_data["redirect_uri_provided_explicitly"] == "True",
                expires_at=time.time() + 300,  # 5 minutes
                scopes=["openid", "profile", "email"],  # Default scopes
                code_challenge=state_data.get("code_challenge"),
            )

            # Store the original Auth0 code temporarily
            auth_code.code = code  # Temporarily store Auth0 code
            self.auth_codes[mcp_code] = auth_code
            auth_code.code = mcp_code  # Restore MCP code

            # Clean up state mapping
            del self.state_mapping[state]

            # Redirect back to client
            redirect_url = construct_redirect_uri(
                state_data["redirect_uri"],
                code=mcp_code,
                state=state
            )

            logger.info(f"Successful Auth0 callback for client {state_data['client_id']}")
            return RedirectResponse(url=redirect_url, status_code=302)

        except Exception as e:
            logger.error(f"Auth0 callback handling failed: {e}")
            if isinstance(e, Auth0Error):
                raise HTTPException(status_code=400, detail=str(e))
            raise HTTPException(status_code=500, detail="Internal server error")

    async def get_client_credentials(self) -> Dict[str, str]:
        """Get Auth0 client credentials for debugging."""
        return {
            "domain": self.auth0_config.domain,
            "client_id": self.auth0_config.client_id,
            "audience": self.auth0_config.audience or "Not configured",
        }