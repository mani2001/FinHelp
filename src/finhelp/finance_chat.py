# src/finhelp/finance_chat.py
from openai import OpenAI
from .config import settings
from .mcp_client import mcp_session
from mcp import types
import json


async def search_web(query: str, max_results: int = 5) -> list:
    """
    Search the web using Tavily MCP for finance-related information.
    
    Args:
        query: Search query
        max_results: Number of results to return
    
    Returns:
        List of search results with title, url, snippet
    """
    async with mcp_session() as session:
        tools = await session.list_tools()
        search_tool = None
        for tool in tools.tools:
            if "search" in tool.name.lower():
                search_tool = tool.name
                break
        
        if not search_tool:
            raise RuntimeError("No search tool available")
        
        result: types.CallToolResult = await session.call_tool(
            search_tool,
            arguments={
                "query": query,
                "max_results": max_results,
                "include_raw_content": False
            }
        )
        
        results = []
        if result.content:
            for block in result.content:
                if hasattr(block, "text"):
                    try:
                        data = json.loads(block.text)
                        if isinstance(data, dict) and "results" in data:
                            for item in data["results"][:max_results]:
                                results.append({
                                    "title": item.get("title", ""),
                                    "url": item.get("url", ""),
                                    "snippet": item.get("content", "")[:300]
                                })
                    except:
                        continue
        
        return results


async def finance_chat(user_message: str, conversation_history: list = None) -> dict:
    """
    Finance chat with guardrails and web search capability.
    
    Args:
        user_message: User's question
        conversation_history: Previous conversation messages
    
    Returns:
        {
            "response": "Assistant response",
            "sources": ["url1", "url2", ...],
            "conversation": updated conversation history
        }
    """
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    if conversation_history is None:
        conversation_history = []
    
    # Define the web search tool
    tools = [
        {
            "type": "function",
            "function": {
                "name": "search_finance_info",
                "description": "Search the web for real-time financial information, company data, market news, stock prices, economic indicators, or any finance-related topic. Use this when you need current information.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query for financial information"
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    ]
    
    # System prompt with guardrails
    system_prompt = """You are a helpful finance assistant. You ONLY answer questions related to:
- Finance, investing, trading, stocks, bonds, ETFs
- Companies, business models, corporate finance
- Economic concepts, markets, GDP, inflation
- Personal finance, budgeting, retirement planning
- Financial ratios, analysis, accounting

If someone asks about non-finance topics (sports, entertainment, politics, cooking, etc.), politely decline and say:
"I'm specialized in finance topics. I can help you with questions about investing, companies, markets, or economic concepts. How can I assist you with finance?"

When answering finance questions:
- Use the search tool to get current, accurate information
- Cite your sources
- Be clear and professional
- Explain complex concepts simply"""

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_message})
    
    # First LLM call
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=tools,
        tool_choice="auto",
        temperature=0.3
    )
    
    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls
    sources = []
    
    # Check if LLM wants to search
    if tool_calls:
        tool_call = tool_calls[0]
        function_args = json.loads(tool_call.function.arguments)
        search_query = function_args.get("query", "")
        
        # Perform web search
        search_results = await search_web(search_query, max_results=5)
        
        # Extract sources
        sources = [r["url"] for r in search_results if r["url"]]
        
        # Format results for LLM
        search_results_text = "\n\n".join([
            f"Title: {r['title']}\nURL: {r['url']}\nSnippet: {r['snippet']}"
            for r in search_results
        ])
        
        # Add tool response
        messages.append(response_message)
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": tool_call.function.name,
            "content": search_results_text
        })
        
        # Get final response
        final_response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.3
        )
        
        final_message = final_response.choices[0].message.content
        
    else:
        # No search needed - direct response
        final_message = response_message.content
    
    # Update conversation history
    conversation_history.append({"role": "user", "content": user_message})
    conversation_history.append({"role": "assistant", "content": final_message})
    
    return {
        "response": final_message,
        "sources": sources,
        "conversation": conversation_history
    }