"""Agent Blueprint management using Agent Framework.

This module provides functionality to define and manage agent blueprints
that specify capabilities and configurations for agents.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from agent_framework_core import AgentBlueprint, AgentCapability

logger = logging.getLogger(__name__)


class AgentBlueprintManager:
    """Manages agent blueprint creation and configuration."""
    
    def __init__(
        self,
        blueprint_name: Optional[str] = None,
    ):
        """Initialize Agent Blueprint Manager.
        
        Args:
            blueprint_name: Name of the agent blueprint
        """
        self.blueprint_name = blueprint_name or os.getenv("AGENT_BLUEPRINT_NAME", "")
        self.blueprint = None
        
        logger.info(f"AgentBlueprintManager initialized: {self.blueprint_name}")
    
    def create_blueprint(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentBlueprint:
        """Create a new agent blueprint.
        
        Args:
            name: Name of the blueprint
            description: Description of the blueprint
            capabilities: List of capability names
            metadata: Optional metadata for the blueprint
            
        Returns:
            AgentBlueprint instance
        """
        try:
            blueprint_name = name or self.blueprint_name
            
            if not blueprint_name:
                raise ValueError("Blueprint name is required")
            
            logger.info(f"Creating agent blueprint: {blueprint_name}")
            
            # Define default capabilities for Azure AI Search agent
            if not capabilities:
                capabilities = [
                    "search_documents",
                    "retrieve_document",
                    "authenticate_to_azure",
                ]
            
            # Create capability objects
            capability_objects = []
            for cap_name in capabilities:
                capability = AgentCapability(
                    name=cap_name,
                    description=f"Capability: {cap_name}",
                )
                capability_objects.append(capability)
            
            # Create the blueprint
            self.blueprint = AgentBlueprint(
                name=blueprint_name,
                description=description or f"Blueprint for {blueprint_name}",
                capabilities=capability_objects,
                metadata=metadata or {},
            )
            
            logger.info(f"Agent blueprint created: {blueprint_name}")
            return self.blueprint
            
        except Exception as e:
            logger.error(f"Failed to create agent blueprint: {e}")
            raise
    
    def get_blueprint(self) -> Optional[AgentBlueprint]:
        """Get the current agent blueprint.
        
        Returns:
            AgentBlueprint instance or None
        """
        return self.blueprint
    
    def add_capability(
        self,
        capability_name: str,
        capability_description: Optional[str] = None,
    ) -> None:
        """Add a capability to the blueprint.
        
        Args:
            capability_name: Name of the capability
            capability_description: Optional description
        """
        if not self.blueprint:
            raise ValueError("Blueprint must be created first")
        
        try:
            capability = AgentCapability(
                name=capability_name,
                description=capability_description or f"Capability: {capability_name}",
            )
            
            self.blueprint.capabilities.append(capability)
            logger.info(f"Added capability: {capability_name}")
            
        except Exception as e:
            logger.error(f"Failed to add capability: {e}")
            raise
    
    def get_blueprint_info(self) -> Dict[str, Any]:
        """Get blueprint information as dictionary.
        
        Returns:
            Dictionary with blueprint details
        """
        if not self.blueprint:
            return {}
        
        return {
            "name": self.blueprint.name,
            "description": self.blueprint.description,
            "capabilities": [cap.name for cap in self.blueprint.capabilities],
            "metadata": self.blueprint.metadata,
        }
    
    def validate_blueprint(self) -> bool:
        """Validate that the blueprint is properly configured.
        
        Returns:
            True if valid, False otherwise
        """
        try:
            if not self.blueprint:
                logger.error("No blueprint created")
                return False
            
            if not self.blueprint.name:
                logger.error("Blueprint name is missing")
                return False
            
            if not self.blueprint.capabilities:
                logger.warning("Blueprint has no capabilities")
            
            logger.info("Blueprint validation successful")
            return True
            
        except Exception as e:
            logger.error(f"Blueprint validation failed: {e}")
            return False
