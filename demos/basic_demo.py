"""
Basic MCP OAuth Demo

This demo shows the complete OAuth authentication flow between
an MCP client and server.
"""

import asyncio
import logging
import sys
import subprocess
import time
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from client.client import MCPOAuthClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def wait_for_server(url: str, timeout: int = 30) -> bool:
    """Wait for the MCP server to be ready."""
    import httpx

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{url}/health")
                if response.status_code == 200:
                    return True
        except:
            pass
        await asyncio.sleep(1)
    return False


async def demo_oauth_flow():
    """Demonstrate the complete OAuth flow."""
    print("🚀 MCP OAuth Basic Demo")
    print("=" * 50)

    server_url = "http://localhost:8000"

    # Wait for server to be ready
    print("⏳ Waiting for MCP server to be ready...")
    if not await wait_for_server(server_url):
        print("❌ MCP server is not running!")
        print("💡 Please start the server first with: uv run python server/app.py")
        return False

    print("✅ MCP server is ready!")

    # Create client
    print("\n🔧 Creating MCP OAuth client...")
    client = MCPOAuthClient(server_url)

    try:
        # Step 1: Authentication
        print("\n" + "="*30)
        print("STEP 1: OAuth Authentication")
        print("="*30)

        print("🔐 Starting OAuth authentication flow...")
        print("📱 This will open your browser for authentication")

        if not await client.authenticate():
            print("❌ Authentication failed!")
            return False

        print("✅ Authentication successful!")

        # Step 2: Connection
        print("\n" + "="*30)
        print("STEP 2: MCP Server Connection")
        print("="*30)

        if not await client.connect():
            print("❌ Connection failed!")
            return False

        print("✅ Connected to MCP server!")

        # Step 3: List Tools
        print("\n" + "="*30)
        print("STEP 3: List Available Tools")
        print("="*30)

        tools = await client.list_tools()
        print(f"📋 Found {len(tools.get('tools', []))} available tools:")

        for i, tool in enumerate(tools.get('tools', []), 1):
            print(f"  {i}. {tool['name']}")
            print(f"     Description: {tool['description']}")

        # Step 4: Call Tools
        print("\n" + "="*30)
        print("STEP 4: Call MCP Tools")
        print("="*30)

        # Call get_user_info
        print("🔧 Calling get_user_info tool...")
        result = await client.call_tool("get_user_info", {})
        print(f"✅ Result: {result['result']}")

        # Call get_weather
        print("\n🔧 Calling get_weather tool...")
        result = await client.call_tool("get_weather", {"city": "London"})
        print(f"✅ Weather result: {result['result']}")

        # Call protected_action
        print("\n🔧 Calling protected_action tool...")
        result = await client.call_tool("protected_action", {"action": "demo_action"})
        print(f"✅ Action result: {result['result']}")

        # Step 5: Cleanup
        print("\n" + "="*30)
        print("STEP 5: Cleanup")
        print("="*30)

        await client.disconnect()
        print("✅ Disconnected from server")

        print("\n🎉 Demo completed successfully!")
        print("💡 The OAuth flow worked end-to-end!")

        return True

    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        await client.disconnect()
        return False


async def interactive_demo():
    """Run an interactive demo where user can try different tools."""
    print("🎮 Interactive MCP OAuth Demo")
    print("=" * 50)

    server_url = input("Enter MCP server URL (default: http://localhost:8000): ").strip()
    if not server_url:
        server_url = "http://localhost:8000"

    # Check if server is running
    if not await wait_for_server(server_url):
        print("❌ MCP server is not running!")
        print("💡 Please start the server first with: uv run python server/app.py")
        return False

    client = MCPOAuthClient(server_url)

    try:
        # Authenticate
        print("\n🔐 Authenticating...")
        if not await client.authenticate():
            print("❌ Authentication failed!")
            return False

        # Connect
        if not await client.connect():
            print("❌ Connection failed!")
            return False

        print("✅ Connected! You can now interact with the MCP server.")

        # Interactive loop
        while True:
            print("\n" + "="*40)
            print("What would you like to do?")
            print("1. List available tools")
            print("2. Get weather for a city")
            print("3. Get user information")
            print("4. Perform a protected action")
            print("5. Exit")

            choice = input("\nEnter choice (1-5): ").strip()

            if choice == "1":
                tools = await client.list_tools()
                print("\n📋 Available tools:")
                for tool in tools.get('tools', []):
                    print(f"  • {tool['name']} - {tool['description']}")

            elif choice == "2":
                city = input("Enter city name: ").strip()
                if city:
                    result = await client.call_tool("get_weather", {"city": city})
                    print(f"🌤️  {result['result']}")

            elif choice == "3":
                result = await client.call_tool("get_user_info", {})
                print(f"👤 {result['result']}")

            elif choice == "4":
                action = input("Enter action to perform: ").strip()
                if action:
                    result = await client.call_tool("protected_action", {"action": action})
                    print(f"🔧 {result['result']}")

            elif choice == "5":
                break

            else:
                print("❌ Invalid choice. Please enter 1-5.")

        await client.disconnect()
        print("\n👋 Thanks for trying the demo!")
        return True

    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted by user")
        await client.disconnect()
        return True
    except Exception as e:
        print(f"\n❌ Demo error: {e}")
        await client.disconnect()
        return False


def main():
    """Main demo entry point."""
    print("Choose demo mode:")
    print("1. Automated demo (shows complete flow)")
    print("2. Interactive demo (you control the actions)")

    choice = input("\nEnter choice (1-2): ").strip()

    if choice == "1":
        success = asyncio.run(demo_oauth_flow())
    elif choice == "2":
        success = asyncio.run(interactive_demo())
    else:
        print("❌ Invalid choice")
        return 1

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)