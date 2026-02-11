"""Agent Identity management using Agent Identity Python SDK.

This module provides functionality to create and manage agent identities
for authentication with Azure services.
"""

import os
import logging
from typing import Optional, Dict, Any
from azure.identity import DefaultAzureCredential, ClientSecretCredential
from agent_identity_python_sdk import AgentIdentityClient, AgentIdentityConfig

logger = logging.getLogger(__name__)


class AgentIdentityManager:
    """Manages agent identity creation and token acquisition."""
    
    def __init__(
        self,
        client_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        audience: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        """Initialize Agent Identity Manager.
        
        Args:
            client_id: Azure AD client ID for the agent identity
            tenant_id: Azure AD tenant ID
            audience: Target audience for the agent identity tokens
            client_secret: Optional client secret for authentication
        """
        self.client_id = client_id or os.getenv("AGENT_IDENTITY_CLIENT_ID", "")
        self.tenant_id = tenant_id or os.getenv("AGENT_IDENTITY_TENANT_ID", "")
        self.audience = audience or os.getenv("AGENT_IDENTITY_AUDIENCE", "")
        self.client_secret = client_secret or os.getenv("AZURE_CLIENT_SECRET", "")
        
        # Initialize credential
        if self.client_secret and self.client_id and self.tenant_id:
            self.credential = ClientSecretCredential(
                tenant_id=self.tenant_id,
                client_id=self.client_id,
                client_secret=self.client_secret,
            )
            logger.info("Initialized with ClientSecretCredential")
        else:
            self.credential = DefaultAzureCredential()
            logger.info("Initialized with DefaultAzureCredential")
        
        # Initialize agent identity client
        self.config = AgentIdentityConfig(
            tenant_id=self.tenant_id,
            client_id=self.client_id,
            audience=self.audience,
        )
        self.client = AgentIdentityClient(
            credential=self.credential,
            config=self.config,
        )
        
        logger.info(f"AgentIdentityManager initialized for tenant: {self.tenant_id}")
    
    def create_agent_identity(
        self,
        agent_name: str,
        blueprint_name: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new agent identity.
        
        Args:
            agent_name: Name of the agent
            blueprint_name: Optional blueprint name to associate
            description: Optional description of the agent
            metadata: Optional metadata for the agent
            
        Returns:
            Dictionary containing agent identity details
        """
        try:
            logger.info(f"Creating agent identity: {agent_name}")
            
            identity_data = {
                "name": agent_name,
                "tenant_id": self.tenant_id,
                "client_id": self.client_id,
                "audience": self.audience,
            }
            
            if blueprint_name:
                identity_data["blueprint_name"] = blueprint_name
            if description:
                identity_data["description"] = description
            if metadata:
                identity_data["metadata"] = metadata
            
            # Create agent identity using SDK
            result = self.client.create_identity(identity_data)
            
            logger.info(f"Agent identity created successfully: {agent_name}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to create agent identity: {e}")
            raise
    
    def get_agent_token(
        self,
        scopes: Optional[list[str]] = None,
    ) -> str:
        """Acquire access token for the agent identity.
        
        Args:
            scopes: List of OAuth scopes to request
            
        Returns:
            Access token string
        """
        try:
            if not scopes:
                # Default to Azure AI Search scope
                scopes = ["https://search.azure.com/.default"]
            
            logger.info(f"Acquiring token for scopes: {scopes}")
            
            # Get token using the credential
            token = self.credential.get_token(*scopes)
            
            logger.info("Token acquired successfully")
            return token.token
            
        except Exception as e:
            logger.error(f"Failed to acquire agent token: {e}")
            raise
    
    def get_identity_info(self) -> Dict[str, str]:
        """Get current agent identity information.
        
        Returns:
            Dictionary with identity details
        """
        return {
            "client_id": self.client_id,
            "tenant_id": self.tenant_id,
            "audience": self.audience,
        }
    
    def validate_identity(self) -> bool:
        """Validate that the agent identity is properly configured.
        
        Returns:
            True if valid, False otherwise
        """
        try:
            if not self.client_id or not self.tenant_id:
                logger.error("Missing required identity configuration")
                return False
            
            # Try to get a token to validate
            token = self.get_agent_token()
            if token:
                logger.info("Agent identity validation successful")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Agent identity validation failed: {e}")
            return False
