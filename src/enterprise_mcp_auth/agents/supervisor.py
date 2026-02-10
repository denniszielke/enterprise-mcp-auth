"""Supervisor graph for managing identity and agent execution.

This module implements a LangGraph supervisor that:
1. Validates identity/token exists
2. Creates MCP client
3. Runs the ReAct agent
"""

from typing import Optional
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END
from .state import AgentState, IdentityContext
from .react_agent import run_react_agent


def validate_identity(state: AgentState) -> AgentState:
    """Validate that identity context exists and is valid.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state (unchanged if valid)
        
    Raises:
        ValueError: If identity is missing or invalid
    """
    identity = state.get("identity")
    
    if not identity:
        raise ValueError("Identity context is missing")
    
    if not identity.get("access_token"):
        raise ValueError("Access token is missing from identity context")
    
    if not state.get("mcp_base_url"):
        raise ValueError("MCP base URL is missing")
    
    # Identity is valid, return state unchanged
    return state


def should_continue(state: AgentState) -> str:
    """Determine if the agent should continue or end.
    
    Args:
        state: Current agent state
        
    Returns:
        "end" to finish execution
    """
    # After agent runs, we're done
    return "end"


def create_supervisor_graph(model_name: str = "gpt-4o-mini") -> StateGraph:
    """Create the supervisor graph.
    
    The graph flow:
    1. validate_identity: Check identity exists
    2. run_agent: Execute ReAct agent with MCP tools
    3. END
    
    Args:
        model_name: OpenAI model name for the agent
        
    Returns:
        Compiled StateGraph
    """
    # Create graph
    graph = StateGraph(AgentState)
    
    # Add nodes
    graph.add_node("validate_identity", validate_identity)
    
    # Create agent node with model configuration
    async def agent_node(state: AgentState) -> AgentState:
        return await run_react_agent(state, model_name=model_name)
    
    graph.add_node("run_agent", agent_node)
    
    # Add edges
    graph.set_entry_point("validate_identity")
    graph.add_edge("validate_identity", "run_agent")
    graph.add_edge("run_agent", END)
    
    # Compile graph
    return graph.compile()


async def run_supervisor(
    query: str,
    access_token: str,
    mcp_base_url: str,
    user_login: Optional[str] = None,
    oid: Optional[str] = None,
    model_name: str = "gpt-4o-mini"
) -> dict:
    """Run the supervisor graph with a user query.
    
    This is a convenience function that creates the identity context,
    initializes the state, and runs the supervisor graph.
    
    Args:
        query: User's query string
        access_token: OAuth access token for MCP authentication
        mcp_base_url: Base URL of the MCP server
        user_login: Optional user login name
        oid: Optional user object ID
        model_name: OpenAI model name for the agent
        
    Returns:
        Final state dictionary after execution
    """
    # Create identity context
    identity: IdentityContext = {
        "user_login": user_login,
        "access_token": access_token,
        "oid": oid,
    }
    
    # Initialize state
    initial_state: AgentState = {
        "messages": [],
        "identity": identity,
        "query": query,
        "mcp_base_url": mcp_base_url,
    }
    
    # Create and run supervisor
    supervisor = create_supervisor_graph(model_name=model_name)
    result = await supervisor.ainvoke(initial_state)
    
    return result
