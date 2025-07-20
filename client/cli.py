"""
Command Line Interface for MCP OAuth Client

A simple CLI for testing and demonstrating the MCP OAuth client.
"""

import asyncio
import logging
import sys
from typing import Optional

from client.client import MCPOAuthClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def main():
    """Main CLI entry point."""
    print("🚀 MCP OAuth Client CLI")
    print("=" * 40)

    # Get server URL
    server_url = input("Enter MCP server URL (default: http://localhost:8000): ").strip()
    if not server_url:
        server_url = "http://localhost:8000"

    # Create client
    client = MCPOAuthClient(server_url)

    try:
        # Authenticate
        print("\n🔐 Starting OAuth authentication...")
        if not await client.authenticate():
            print("❌ Authentication failed!")
            return 1

        # Connect
        print("\n🔌 Connecting to MCP server...")
        if not await client.connect():
            print("❌ Connection failed!")
            return 1

        # Interactive loop
        while True:
            print("\n" + "=" * 40)
            print("Available commands:")
            print("1. List tools")
            print("2. Call tool")
            print("3. Exit")

            choice = input("\nEnter choice (1-3): ").strip()

            if choice == "1":
                await list_tools_command(client)
            elif choice == "2":
                await call_tool_command(client)
            elif choice == "3":
                break
            else:
                print("❌ Invalid choice. Please enter 1, 2, or 3.")

        # Disconnect
        await client.disconnect()
        print("\n👋 Goodbye!")
        return 0

    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user")
        await client.disconnect()
        return 0
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        await client.disconnect()
        return 1


async def list_tools_command(client: MCPOAuthClient):
    """Handle list tools command."""
    try:
        print("\n📋 Listing available tools...")
        tools = await client.list_tools()

        print(f"\n✅ Found {len(tools.get('tools', []))} tools:")
        for i, tool in enumerate(tools.get('tools', []), 1):
            print(f"  {i}. {tool['name']} - {tool['description']}")

    except Exception as e:
        print(f"❌ Failed to list tools: {e}")


async def call_tool_command(client: MCPOAuthClient):
    """Handle call tool command."""
    try:
        # Get available tools first
        tools = await client.list_tools()
        tool_list = tools.get('tools', [])

        if not tool_list:
            print("❌ No tools available")
            return

        # Show available tools
        print("\nAvailable tools:")
        for i, tool in enumerate(tool_list, 1):
            print(f"  {i}. {tool['name']} - {tool['description']}")

        # Get tool selection
        while True:
            try:
                choice = int(input(f"\nSelect tool (1-{len(tool_list)}): "))
                if 1 <= choice <= len(tool_list):
                    selected_tool = tool_list[choice - 1]
                    break
                else:
                    print(f"❌ Please enter a number between 1 and {len(tool_list)}")
            except ValueError:
                print("❌ Please enter a valid number")

        # Get tool arguments
        tool_name = selected_tool['name']
        arguments = {}

        if tool_name == "get_weather":
            city = input("Enter city name: ").strip()
            if city:
                arguments["city"] = city
        elif tool_name == "protected_action":
            action = input("Enter action to perform: ").strip()
            if action:
                arguments["action"] = action
        # For get_user_info, no arguments needed

        # Call the tool
        print(f"\n🔧 Calling tool '{tool_name}' with arguments: {arguments}")
        result = await client.call_tool(tool_name, arguments)

        print(f"\n✅ Tool result:")
        print(f"   Status: {result.get('status', 'unknown')}")
        print(f"   Result: {result.get('result', 'No result')}")

    except Exception as e:
        print(f"❌ Failed to call tool: {e}")


def cli_main():
    """Entry point for CLI script."""
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Interrupted by user")
        sys.exit(0)


if __name__ == "__main__":
    cli_main()