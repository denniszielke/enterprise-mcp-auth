"""Azure AI Search MCP Client with FastMCP OAuth authentication.

This module implements a CLI client that connects to the Azure AI Search MCP
server using FastMCP's built-in OAuth flow (browser-based authorization).
"""

import os
import sys
import argparse
import asyncio
from dotenv import load_dotenv
from fastmcp import Client

# Load environment variables
load_dotenv()

# Environment variables
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp")


async def search_documents_command(client: Client, query: str, top: int):
    """Execute search_documents tool."""
    print(f"\n🔍 Searching for: '{query}' (top {top} results)")
    print("-" * 60)
    
    try:
        result = await client.call_tool("search_documents", {"query": query, "top": top})
        
        if not result:
            print("No results found.")
            return
        
        for i, doc in enumerate(result, 1):
            print(f"\nResult {i}:")
            for key, value in doc.items():
                print(f"  {key}: {value}")
    except Exception as e:
        print(f"Error: {e}")


async def get_document_command(client: Client, doc_id: str):
    """Execute get_document tool."""
    print(f"\n📄 Getting document with ID: '{doc_id}'")
    print("-" * 60)
    
    try:
        result = await client.call_tool("get_document", {"id": doc_id})
        
        if "error" in result:
            print(f"Error: {result['error']}")
            return
        
        print("\nDocument:")
        for key, value in result.items():
            print(f"  {key}: {value}")
    except Exception as e:
        print(f"Error: {e}")


async def suggest_command(client: Client, query: str, top: int):
    """Execute suggest tool."""
    print(f"\n💡 Getting suggestions for: '{query}' (top {top} results)")
    print("-" * 60)
    
    try:
        result = await client.call_tool("suggest", {"query": query, "top": top})
        
        if not result:
            print("No suggestions found.")
            return
        
        for i, doc in enumerate(result, 1):
            print(f"\nSuggestion {i}:")
            for key, value in doc.items():
                print(f"  {key}: {value}")
    except Exception as e:
        print(f"Error: {e}")


async def list_tools_command(client: Client):
    """List available tools."""
    print("\n🛠️  Available Tools:")
    print("-" * 60)
    
    try:
        tools = await client.list_tools()
        
        for tool in tools:
            print(f"\n• {tool.name}")
            if hasattr(tool, 'description') and tool.description:
                print(f"  {tool.description}")
            if hasattr(tool, 'inputSchema') and tool.inputSchema:
                schema = tool.inputSchema
                if 'properties' in schema:
                    print("  Parameters:")
                    for param_name, param_info in schema['properties'].items():
                        param_type = param_info.get('type', 'any')
                        param_desc = param_info.get('description', '')
                        print(f"    - {param_name} ({param_type}): {param_desc}")
    except Exception as e:
        print(f"Error: {e}")


async def run_client(server_url: str, command: str, **kwargs):
    """Run the MCP client with specified command.
    
    Args:
        server_url: MCP server URL
        command: Command to execute
        **kwargs: Additional command arguments
    """
    # Use FastMCP's built-in OAuth flow (browser-based)
    async with Client(server_url, auth="oauth") as client:
        if command == "search":
            await search_documents_command(client, kwargs.get("query"), kwargs.get("top", 5))
        elif command == "get":
            await get_document_command(client, kwargs.get("id"))
        elif command == "suggest":
            await suggest_command(client, kwargs.get("query"), kwargs.get("top", 5))
        elif command == "list-tools":
            await list_tools_command(client)
        else:
            print(f"Unknown command: {command}")
            sys.exit(1)


def main():
    """Main entry point for the MCP client CLI."""
    parser = argparse.ArgumentParser(
        description="Azure AI Search MCP Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List available tools
  python -m enterprise_mcp_auth.client.ai_search_mcp_client list-tools
  
  # Search documents
  python -m enterprise_mcp_auth.client.ai_search_mcp_client search --query "security" --top 5
  
  # Get a specific document
  python -m enterprise_mcp_auth.client.ai_search_mcp_client get --id "doc1"
  
  # Get suggestions
  python -m enterprise_mcp_auth.client.ai_search_mcp_client suggest --query "sec" --top 5
        """
    )
    
    parser.add_argument(
        "command",
        choices=["search", "get", "suggest", "list-tools"],
        help="Command to execute"
    )
    parser.add_argument(
        "--query",
        help="Search query or suggestion query"
    )
    parser.add_argument(
        "--id",
        help="Document ID for get command"
    )
    parser.add_argument(
        "--top",
        type=int,
        default=5,
        help="Maximum number of results (default: 5)"
    )
    parser.add_argument(
        "--server-url",
        default=os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp"),
        help="MCP server URL"
    )
    
    args = parser.parse_args()
    
    # Validate command-specific arguments
    if args.command == "search" and not args.query:
        parser.error("--query is required for search command")
    if args.command == "get" and not args.id:
        parser.error("--id is required for get command")
    if args.command == "suggest" and not args.query:
        parser.error("--query is required for suggest command")
    
    # Use server URL from argument
    server_url = args.server_url

    # Fix common configuration error where /mcp is missing for FastMCP StreamableHttpTransport
    if server_url.rstrip("/") == "http://localhost:8000":
        server_url = "http://localhost:8000/mcp"
    
    print(f"Connecting to MCP server at {server_url}...")
    print("(Your browser will open for authentication if needed)")
    
    # Run the client
    try:
        asyncio.run(run_client(
            server_url=server_url,
            command=args.command,
            query=args.query,
            id=args.id,
            top=args.top
        ))
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
