"""Main Agent implementation using Agent Framework.

This module provides the main agent implementation that uses agent identity
for authentication and agent blueprint for defining capabilities.
"""

import os
import time
import logging
from typing import Optional, Dict, Any, List
from azure.search.documents import SearchClient
from azure.core.credentials import AccessToken
from .agent_identity import AgentIdentityManager
from .agent_blueprint import AgentBlueprintManager

logger = logging.getLogger(__name__)


class TokenCredential:
    """Simple token credential for Azure SDK."""
    
    def __init__(self, token: str):
        """Initialize with access token.
        
        Args:
            token: Access token string
        """
        self.token = token
    
    def get_token(self, *scopes, **kwargs) -> AccessToken:
        """Get access token.
        
        Returns:
            AccessToken instance
        """
        # Return a simple token (expires_on is not critical for this use case)
        return AccessToken(self.token, int(time.time()) + 3600)


class EnterpriseAgent:
    """Enterprise agent with agent identity and blueprint."""
    
    def __init__(
        self,
        agent_name: Optional[str] = None,
        identity_manager: Optional[AgentIdentityManager] = None,
        blueprint_manager: Optional[AgentBlueprintManager] = None,
    ):
        """Initialize Enterprise Agent.
        
        Args:
            agent_name: Name of the agent
            identity_manager: AgentIdentityManager instance
            blueprint_manager: AgentBlueprintManager instance
        """
        self.agent_name = agent_name or os.getenv("AGENT_NAME", "enterprise-agent")
        
        # Initialize identity manager
        if identity_manager:
            self.identity_manager = identity_manager
        else:
            self.identity_manager = AgentIdentityManager()
        
        # Initialize blueprint manager
        if blueprint_manager:
            self.blueprint_manager = blueprint_manager
        else:
            self.blueprint_manager = AgentBlueprintManager()
            self.blueprint_manager.create_blueprint(
                name=self.agent_name,
                description=f"Enterprise agent: {self.agent_name}",
            )
        
        logger.info(f"EnterpriseAgent initialized: {self.agent_name}")
    
    def authenticate(self, scopes: Optional[List[str]] = None) -> str:
        """Authenticate the agent and get access token.
        
        Args:
            scopes: List of OAuth scopes to request
            
        Returns:
            Access token string
        """
        try:
            logger.info(f"Authenticating agent: {self.agent_name}")
            token = self.identity_manager.get_agent_token(scopes=scopes)
            logger.info("Agent authenticated successfully")
            return token
            
        except Exception as e:
            logger.error(f"Agent authentication failed: {e}")
            raise
    
    def get_azure_search_client(
        self,
        endpoint: Optional[str] = None,
        index_name: Optional[str] = None,
    ) -> SearchClient:
        """Get authenticated Azure AI Search client.
        
        Args:
            endpoint: Azure AI Search endpoint
            index_name: Index name
            
        Returns:
            SearchClient instance
        """
        try:
            endpoint = endpoint or os.getenv("AZURE_SEARCH_ENDPOINT", "")
            index_name = index_name or os.getenv("AZURE_SEARCH_INDEX", "documents")
            
            if not endpoint:
                raise ValueError("Azure Search endpoint is required")
            
            logger.info(f"Creating Azure Search client for index: {index_name}")
            
            # Get access token for Azure AI Search
            token = self.authenticate(scopes=["https://search.azure.com/.default"])
            
            # Create token credential
            credential = TokenCredential(token)
            
            # Create search client
            search_client = SearchClient(
                endpoint=endpoint,
                index_name=index_name,
                credential=credential,
            )
            
            logger.info("Azure Search client created successfully")
            return search_client
            
        except Exception as e:
            logger.error(f"Failed to create Azure Search client: {e}")
            raise
    
    def search_documents(
        self,
        query: str,
        top: int = 5,
        search_client: Optional[SearchClient] = None,
    ) -> List[Dict[str, Any]]:
        """Search documents using Azure AI Search.
        
        Args:
            query: Search query
            top: Number of results to return
            search_client: Optional SearchClient instance
            
        Returns:
            List of document dictionaries
        """
        try:
            logger.info(f"Searching documents: query={query}, top={top}")
            
            # Get or create search client
            if not search_client:
                search_client = self.get_azure_search_client()
            
            # Execute search
            results = search_client.search(
                search_text=query,
                top=top,
                include_total_count=True,
            )
            
            # Convert results to list of dictionaries
            documents = []
            for result in results:
                doc = dict(result)
                documents.append(doc)
            
            logger.info(f"Found {len(documents)} documents")
            return documents
            
        except Exception as e:
            logger.error(f"Document search failed: {e}")
            raise
    
    def get_document(
        self,
        document_id: str,
        search_client: Optional[SearchClient] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get a specific document by ID.
        
        Args:
            document_id: Document ID
            search_client: Optional SearchClient instance
            
        Returns:
            Document dictionary or None
        """
        try:
            logger.info(f"Getting document: {document_id}")
            
            # Get or create search client
            if not search_client:
                search_client = self.get_azure_search_client()
            
            # Get document
            document = search_client.get_document(key=document_id)
            
            logger.info(f"Retrieved document: {document_id}")
            return dict(document)
            
        except Exception as e:
            logger.error(f"Failed to get document: {e}")
            raise
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get agent information.
        
        Returns:
            Dictionary with agent details
        """
        return {
            "name": self.agent_name,
            "identity": self.identity_manager.get_identity_info(),
            "blueprint": self.blueprint_manager.get_blueprint_info(),
        }
    
    def validate(self) -> bool:
        """Validate agent configuration.
        
        Returns:
            True if valid, False otherwise
        """
        try:
            logger.info(f"Validating agent: {self.agent_name}")
            
            # Validate identity
            if not self.identity_manager.validate_identity():
                logger.error("Identity validation failed")
                return False
            
            # Validate blueprint
            if not self.blueprint_manager.validate_blueprint():
                logger.error("Blueprint validation failed")
                return False
            
            logger.info("Agent validation successful")
            return True
            
        except Exception as e:
            logger.error(f"Agent validation failed: {e}")
            return False
