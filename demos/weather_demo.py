"""
Weather Demo for MCP OAuth

This demo focuses on the weather tool functionality,
showing how to authenticate and call weather-related tools.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from client.client import MCPOAuthClient


async def weather_demo():
    """Demonstrate weather tool functionality."""
    print("🌤️  MCP OAuth Weather Demo")
    print("=" * 40)

    server_url = "http://localhost:8000"

    # Create client
    client = MCPOAuthClient(server_url)

    try:
        # Authenticate
        print("🔐 Authenticating with MCP server...")
        if not await client.authenticate():
            print("❌ Authentication failed!")
            return False

        # Connect
        print("🔌 Connecting to MCP server...")
        if not await client.connect():
            print("❌ Connection failed!")
            return False

        print("✅ Connected successfully!")

        # Demo: Multiple weather queries
        cities = ["London", "Tokyo", "New York", "Paris", "Sydney"]

        print(f"\n🌍 Getting weather for {len(cities)} cities...")
        print("=" * 40)

        for city in cities:
            print(f"\n🌤️  Getting weather for {city}...")

            try:
                result = await client.call_tool("get_weather", {"city": city})

                if result.get('status') == 'success':
                    print(f"✅ {city}: {result['result']}")
                else:
                    print(f"❌ {city}: Failed to get weather")

            except Exception as e:
                print(f"❌ {city}: Error - {e}")

        # Interactive weather queries
        print(f"\n🎮 Interactive Weather Queries")
        print("=" * 40)
        print("Enter city names to get weather (or 'quit' to exit)")

        while True:
            city = input("\n🌍 Enter city name: ").strip()

            if city.lower() in ['quit', 'exit', 'q']:
                break

            if not city:
                print("❌ Please enter a city name")
                continue

            try:
                print(f"🔍 Getting weather for {city}...")
                result = await client.call_tool("get_weather", {"city": city})

                if result.get('status') == 'success':
                    print(f"✅ Weather: {result['result']}")
                else:
                    print(f"❌ Failed to get weather for {city}")

            except Exception as e:
                print(f"❌ Error getting weather: {e}")

        # Cleanup
        await client.disconnect()
        print("\n✅ Weather demo completed!")
        return True

    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted by user")
        await client.disconnect()
        return True
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        await client.disconnect()
        return False


async def batch_weather_demo():
    """Demonstrate batch weather queries."""
    print("📊 Batch Weather Demo")
    print("=" * 30)

    server_url = "http://localhost:8000"
    client = MCPOAuthClient(server_url)

    try:
        # Authenticate and connect
        if not await client.authenticate():
            return False
        if not await client.connect():
            return False

        # Get cities from user
        print("\nEnter cities for batch weather query:")
        print("(Enter city names separated by commas)")

        cities_input = input("Cities: ").strip()
        if not cities_input:
            cities = ["London", "Tokyo", "New York"]  # Default cities
            print(f"Using default cities: {', '.join(cities)}")
        else:
            cities = [city.strip() for city in cities_input.split(',') if city.strip()]

        print(f"\n📡 Querying weather for {len(cities)} cities...")

        # Batch queries (sequential for this demo)
        results = []
        for i, city in enumerate(cities, 1):
            print(f"  [{i}/{len(cities)}] {city}...", end=" ")

            try:
                result = await client.call_tool("get_weather", {"city": city})
                results.append((city, result))
                print("✅")
            except Exception as e:
                results.append((city, {"error": str(e)}))
                print("❌")

        # Display results
        print(f"\n📋 Weather Results Summary:")
        print("=" * 50)

        for city, result in results:
            if 'error' in result:
                print(f"❌ {city:15} - Error: {result['error']}")
            else:
                print(f"✅ {city:15} - {result.get('result', 'No data')}")

        await client.disconnect()
        return True

    except Exception as e:
        print(f"❌ Batch demo failed: {e}")
        await client.disconnect()
        return False


def main():
    """Main weather demo entry point."""
    print("Choose weather demo mode:")
    print("1. Interactive weather demo")
    print("2. Batch weather demo")

    choice = input("\nEnter choice (1-2): ").strip()

    if choice == "1":
        success = asyncio.run(weather_demo())
    elif choice == "2":
        success = asyncio.run(batch_weather_demo())
    else:
        print("❌ Invalid choice")
        return 1

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)