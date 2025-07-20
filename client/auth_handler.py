"""
OAuth Authentication Handler for MCP Client

Handles the OAuth 2.0 authentication flow for connecting to secured MCP servers.
"""

import asyncio
import logging
import os
import webbrowser
from typing import Optional, Dict, Any
from urllib.parse import urlencode, parse_qs, urlparse
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

import httpx
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


class CallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler for OAuth callback."""

    def do_GET(self):
        """Handle GET request for OAuth callback."""
        query_params = parse_qs(urlparse(self.path).query)

        # Store the authorization code
        if 'code' in query_params:
            self.server.auth_code = query_params['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"""
                <html>
                    <body>
                        <h1>Authentication Successful!</h1>
                        <p>You can close this window and return to your application.</p>
                        <script>window.close();</script>
                    </body>
                </html>
            """)
        elif 'error' in query_params:
            self.server.auth_error = query_params['error'][0]
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(f"""
                <html>
                    <body>
                        <h1>Authentication Failed!</h1>
                        <p>Error: {query_params['error'][0]}</p>
                        <p>You can close this window.</p>
                    </body>
                </html>
            """.encode())

    def log_message(self, format, *args):
        """Suppress log messages."""
        pass


class OAuthHandler:
    """
    OAuth 2.0 authentication handler for MCP clients.

    Handles the complete OAuth flow including:
    - Dynamic client registration (if needed)
    - Authorization code flow
    - Token exchange
    """

    def __init__(
        self,
        server_url: str,
        client_id: Optional[str] = None,
        redirect_uri: str = "http://localhost:8080/callback"
    ):
        """
        Initialize the OAuth handler.

        Args:
            server_url: Base URL of the MCP server
            client_id: Pre-registered client ID (optional)
            redirect_uri: Callback URI for OAuth flow
        """
        self.server_url = server_url.rstrip('/')

        # Load from environment variables if not provided
        self.client_id = client_id or os.getenv("AUTH0_CLIENT_ID")
        self.client_secret = os.getenv("AUTH0_CLIENT_SECRET")
        self.redirect_uri = redirect_uri

        # Extract callback port from redirect URI
        parsed_uri = urlparse(redirect_uri)
        self.callback_port = parsed_uri.port or 8080

    async def discover_oauth_config(self) -> Dict[str, Any]:
        """
        Discover OAuth configuration from the MCP server.

        Returns:
            OAuth configuration from .well-known endpoint
        """
        discovery_url = f"{self.server_url}/.well-known/oauth-authorization-server"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(discovery_url)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Failed to discover OAuth configuration: {e}")
                raise

    async def register_client(self, oauth_config: Dict[str, Any]) -> tuple[str, str]:
        """
        Register a new OAuth client dynamically.

        Args:
            oauth_config: OAuth configuration from discovery

        Returns:
            Tuple of (client_id, client_secret)
        """
        registration_endpoint = oauth_config.get("registration_endpoint")
        if not registration_endpoint:
            raise ValueError("Server does not support dynamic client registration")

        registration_data = {
            "client_name": "MCP OAuth Client",
            "redirect_uris": [self.redirect_uri],
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
            "scope": "openid profile email read:mcp write:mcp"
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    registration_endpoint,
                    json=registration_data,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()

                client_info = response.json()
                return client_info["client_id"], client_info.get("client_secret", "")

            except Exception as e:
                logger.error(f"Failed to register OAuth client: {e}")
                raise

    def start_callback_server(self) -> HTTPServer:
        """Start the HTTP server for OAuth callback."""
        server = HTTPServer(('localhost', self.callback_port), CallbackHandler)
        server.auth_code = None
        server.auth_error = None

        # Start server in a separate thread
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        return server

    async def get_authorization_code(self, oauth_config: Dict[str, Any]) -> str:
        """
        Get authorization code through browser-based OAuth flow.

        Args:
            oauth_config: OAuth configuration

        Returns:
            Authorization code
        """
        # Start callback server
        callback_server = self.start_callback_server()

        try:
            # Build authorization URL
            auth_params = {
                "client_id": self.client_id,
                "response_type": "code",
                "redirect_uri": self.redirect_uri,
                "scope": "openid profile email read:mcp write:mcp",
                "state": "mcp-client-auth",  # Simple state for demo
                # "prompt": "login"  # Uncomment to force login every time
            }

            auth_url = f"{oauth_config['authorization_endpoint']}?{urlencode(auth_params)}"

            print(f"🌐 Opening browser for authentication...")
            print(f"🔗 If browser doesn't open, visit: {auth_url}")

            # Open browser
            webbrowser.open(auth_url)

            # Wait for callback
            print("⏳ Waiting for authentication callback...")

            # Poll for the authorization code
            for _ in range(300):  # 5 minutes timeout
                if callback_server.auth_code:
                    return callback_server.auth_code
                elif callback_server.auth_error:
                    raise ValueError(f"Authorization failed: {callback_server.auth_error}")

                await asyncio.sleep(1)

            raise TimeoutError("Authentication timeout - no callback received")

        finally:
            callback_server.shutdown()

    async def exchange_code_for_token(
        self,
        oauth_config: Dict[str, Any],
        auth_code: str
    ) -> str:
        """
        Exchange authorization code for access token.

        Args:
            oauth_config: OAuth configuration
            auth_code: Authorization code from callback

        Returns:
            Access token
        """
        token_data = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
        }

        # Add client secret if available
        if self.client_secret:
            token_data["client_secret"] = self.client_secret

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    oauth_config["token_endpoint"],
                    data=token_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                response.raise_for_status()

                token_response = response.json()
                return token_response["access_token"]

            except Exception as e:
                logger.error(f"Failed to exchange code for token: {e}")
                raise

    async def authenticate(self) -> Optional[str]:
        """
        Perform complete OAuth authentication flow.

        Returns:
            Access token if successful, None otherwise
        """
        try:
            # 1. Discover OAuth configuration
            print("🔍 Discovering OAuth configuration...")
            oauth_config = await self.discover_oauth_config()

                        # 2. Register client if needed
            if not self.client_id:
                if oauth_config.get("registration_endpoint"):
                    print("📝 Registering OAuth client...")
                    self.client_id, self.client_secret = await self.register_client(oauth_config)
                    print(f"✅ Client registered: {self.client_id}")
                else:
                    print("⚠️  Server doesn't support dynamic registration")
                    print("💡 Add AUTH0_CLIENT_ID and AUTH0_CLIENT_SECRET to your .env file to avoid prompts")
                    self.client_id = input("Enter your Auth0 client ID: ").strip()
                    if not self.client_id:
                        raise ValueError("Client ID is required when registration is not supported")

                    if not self.client_secret:
                        self.client_secret = input("Enter your Auth0 client secret (optional): ").strip()

            # Validate we have required credentials
            if not self.client_id:
                raise ValueError("Client ID is required for OAuth authentication")

            if self.client_id and self.client_secret:
                print(f"🔑 Using Auth0 client: {self.client_id[:8]}...")
            else:
                print(f"🔑 Using Auth0 public client: {self.client_id[:8]}...")

            # 3. Get authorization code
            auth_code = await self.get_authorization_code(oauth_config)
            print(f"✅ Authorization code received")

            # 4. Exchange code for token
            print("🔄 Exchanging code for access token...")
            access_token = await self.exchange_code_for_token(oauth_config, auth_code)
            print("✅ Access token received")

            return access_token

        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            print(f"❌ Authentication failed: {e}")
            return None