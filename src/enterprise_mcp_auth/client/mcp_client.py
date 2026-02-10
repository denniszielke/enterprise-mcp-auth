"""FastMCP client wrapper with bearer token authentication.

This module provides a wrapper around the FastMCP client that automatically
injects the Authorization header with a bearer token for all requests.
"""

from typing import Any, Dict, List, Optional
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport


class AuthenticatedMCPClient:
    """MCP client wrapper that injects bearer token authentication."""
    
    def __init__(self, base_url: str, access_token: str):
        """Initialize the authenticated MCP client.
        
        Args:
            base_url: Base URL of the MCP server (e.g., http://localhost:8000)
            access_token: Bearer token for authentication
        """
        self.base_url = base_url
        self.access_token = access_token
        self._client: Optional[Client] = None
        self._transport: Optional[StreamableHttpTransport] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
    
    async def connect(self):
        """Connect to the MCP server."""
        if self._client is not None:
            return  # Already connected
        
        # Create transport with authentication header
        self._transport = StreamableHttpTransport(
            url=self.base_url,
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
        
        # Create client
        self._client = Client(transport=self._transport)
        await self._client.__aenter__()
    
    async def disconnect(self):
        """Disconnect from the MCP server."""
        if self._client is not None:
            await self._client.__aexit__(None, None, None)
            self._client = None
            self._transport = None
    
    async def list_tools(self) -> List[Any]:
        """List all available tools on the MCP server.
        
        Returns:
            List of tool definitions
        """
        if self._client is None:
            raise RuntimeError("Client not connected. Call connect() first.")
        
        return await self._client.list_tools()
    
    async def call_tool(self, tool_name: str, **kwargs) -> Any:
        """Call a tool on the MCP server.
        
        Args:
            tool_name: Name of the tool to call
            **kwargs: Arguments to pass to the tool
            
        Returns:
            Tool execution result
        """
        if self._client is None:
            raise RuntimeError("Client not connected. Call connect() first.")
        
        return await self._client.call_tool(tool_name, **kwargs)
    
    async def search_documents(self, query: str, top: int = 5) -> List[Dict[str, Any]]:
        """Search documents in Azure AI Search.
        
        Args:
            query: Search query string
            top: Maximum number of results to return (default: 5)
            
        Returns:
            List of matching documents
        """
        return await self.call_tool("search_documents", query=query, top=top)
    
    async def get_document(self, id: str) -> Dict[str, Any]:
        """Get a specific document by ID.
        
        Args:
            id: Document ID
            
        Returns:
            Document fields as a dictionary
        """
        return await self.call_tool("get_document", id=id)
    
    async def suggest(self, query: str, top: int = 5) -> List[Dict[str, Any]]:
        """Get search suggestions.
        
        Args:
            query: Query text for suggestions
            top: Maximum number of suggestions to return (default: 5)
            
        Returns:
            List of suggested documents
        """
        return await self.call_tool("suggest", query=query, top=top)


def create_mcp_client(base_url: str, access_token: str) -> AuthenticatedMCPClient:
    """Factory function to create an authenticated MCP client.
    
    Args:
        base_url: Base URL of the MCP server
        access_token: Bearer token for authentication
        
    Returns:
        AuthenticatedMCPClient instance
    """
    return AuthenticatedMCPClient(base_url, access_token)
