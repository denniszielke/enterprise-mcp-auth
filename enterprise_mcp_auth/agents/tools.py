"""LangChain tool wrappers for MCP tools.

This module provides LangChain tool wrappers that call the MCP server tools
through the authenticated MCP client.
"""

from typing import Any, Dict, List
from langchain_core.tools import tool
from ..client.mcp_client import AuthenticatedMCPClient


class MCPTools:
    """Collection of MCP tools as LangChain tools."""
    
    def __init__(self, mcp_client: AuthenticatedMCPClient):
        """Initialize MCP tools with an authenticated client.
        
        Args:
            mcp_client: Authenticated MCP client instance
        """
        self.mcp_client = mcp_client
        
        # Cache tool instances to avoid recreation
        self._search_documents_tool = None
        self._get_document_tool = None
        self._suggest_tool = None
    
    @property
    def search_documents_tool(self):
        """Create search_documents tool."""
        if self._search_documents_tool is not None:
            return self._search_documents_tool
            
        mcp_client = self.mcp_client
        
        @tool
        async def search_documents(query: str, top: int = 5) -> List[Dict[str, Any]]:
            """Search documents in Azure AI Search with permission filtering.
            
            This tool searches the Azure AI Search index and enforces document-level
            access control using the user's token. Use this to find documents based
            on search queries.
            
            Args:
                query: Search query string to find relevant documents
                top: Maximum number of results to return (default: 5, max: 100)
                
            Returns:
                List of matching documents with their fields
            """
            result = await mcp_client.search_documents(query=query, top=top)
            return result
        
        self._search_documents_tool = search_documents
        return self._search_documents_tool
    
    @property
    def get_document_tool(self):
        """Create get_document tool."""
        if self._get_document_tool is not None:
            return self._get_document_tool
            
        mcp_client = self.mcp_client
        
        @tool
        async def get_document(id: str) -> Dict[str, Any]:
            """Get a specific document by ID with permission filtering.
            
            This tool retrieves a document by its ID and enforces document-level
            access control using the user's token. Use this when you know the
            exact document ID.
            
            Args:
                id: Document ID (key field) to retrieve
                
            Returns:
                Document fields as a dictionary, or error if not found/accessible
            """
            result = await mcp_client.get_document(id=id)
            return result
        
        self._get_document_tool = get_document
        return self._get_document_tool
    
    @property
    def suggest_tool(self):
        """Create suggest tool."""
        if self._suggest_tool is not None:
            return self._suggest_tool
            
        mcp_client = self.mcp_client
        
        @tool
        async def suggest(query: str, top: int = 5) -> List[Dict[str, Any]]:
            """Get search suggestions using the suggester with permission filtering.
            
            This tool provides search suggestions based on the query and enforces
            document-level access control using the user's token. Use this for
            auto-complete or suggestion features.
            
            Args:
                query: Query text for getting suggestions (partial text)
                top: Maximum number of suggestions to return (default: 5, max: 100)
                
            Returns:
                List of suggested documents with their fields
            """
            result = await mcp_client.suggest(query=query, top=top)
            return result
        
        self._suggest_tool = suggest
        return self._suggest_tool
    
    def get_all_tools(self) -> List:
        """Get all MCP tools as a list.
        
        Returns:
            List of LangChain tool instances
        """
        return [
            self.search_documents_tool,
            self.get_document_tool,
            self.suggest_tool,
        ]
