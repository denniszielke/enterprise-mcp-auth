"""State definitions for LangGraph agent graphs.

This module defines the state structures used in the LangGraph agent graphs,
including identity context and agent state.
"""

from typing import Annotated, Optional, Sequence
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class IdentityContext(TypedDict):
    """User identity context with authentication information."""
    
    user_login: Optional[str]
    """User login name (e.g., email or username)"""
    
    access_token: str
    """OAuth access token for MCP server authentication"""
    
    oid: Optional[str]
    """User object ID from Azure AD token"""


class AgentState(TypedDict):
    """State for the agent graph execution."""
    
    messages: Annotated[Sequence[BaseMessage], add_messages]
    """Message history for the conversation"""
    
    identity: IdentityContext
    """User identity context"""
    
    query: str
    """Current user query"""
    
    mcp_base_url: str
    """Base URL of the MCP server"""
