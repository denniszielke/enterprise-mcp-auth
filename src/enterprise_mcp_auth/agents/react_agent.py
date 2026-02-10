"""ReAct agent implementation using LangGraph.

This module implements a ReAct (Reasoning and Acting) agent that can use
MCP tools to search and retrieve documents from Azure AI Search.
"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from .state import AgentState
from .tools import MCPTools
from ..client.mcp_client import AuthenticatedMCPClient


def create_react_agent_executor(
    mcp_client: AuthenticatedMCPClient,
    model_name: str = "gpt-4o-mini",
    temperature: float = 0
):
    """Create a ReAct agent that can use MCP tools.
    
    Args:
        mcp_client: Authenticated MCP client for accessing tools
        model_name: OpenAI model name to use (default: gpt-4o-mini)
        temperature: Model temperature (default: 0 for deterministic)
        
    Returns:
        Compiled LangGraph agent executor
    """
    # Initialize LLM
    llm = ChatOpenAI(model=model_name, temperature=temperature)
    
    # Create MCP tools
    mcp_tools = MCPTools(mcp_client)
    tools = mcp_tools.get_all_tools()
    
    # System prompt for the agent
    system_message = """You are a helpful AI assistant with access to an Azure AI Search index.
    
You have access to the following tools:
- search_documents: Search for documents using natural language queries
- get_document: Retrieve a specific document by its ID
- suggest: Get search suggestions for partial queries

Use these tools to help answer user questions about documents. Always provide clear,
concise answers based on the information retrieved from the search index.

When searching:
1. Use search_documents for general queries
2. Use get_document when you have a specific document ID
3. Use suggest when helping with partial queries or auto-complete

Always cite the documents you use in your answers by mentioning their IDs or titles."""
    
    # Create ReAct agent using LangGraph's prebuilt function
    agent = create_react_agent(
        llm,
        tools,
        state_modifier=system_message
    )
    
    return agent


async def run_react_agent(
    state: AgentState,
    model_name: str = "gpt-4o-mini"
) -> AgentState:
    """Run the ReAct agent on the given state.
    
    This node function creates an MCP client, initializes the ReAct agent,
    and executes it with the user's query.
    
    Args:
        state: Current agent state
        model_name: OpenAI model name to use
        
    Returns:
        Updated agent state with agent's response
    """
    # Create MCP client from identity context
    mcp_client = AuthenticatedMCPClient(
        base_url=state["mcp_base_url"],
        access_token=state["identity"]["access_token"]
    )
    
    try:
        # Connect to MCP server
        await mcp_client.connect()
        
        # Create ReAct agent
        agent = create_react_agent_executor(mcp_client, model_name=model_name)
        
        # Prepare input with the user query
        agent_input = {
            "messages": state.get("messages", []) + [HumanMessage(content=state["query"])]
        }
        
        # Run agent
        result = await agent.ainvoke(agent_input)
        
        # Update state with agent's messages
        return {
            **state,
            "messages": result["messages"]
        }
    finally:
        # Always disconnect
        await mcp_client.disconnect()
