# src/finhelp/mcp_probe.py
import os
import asyncio
from dotenv import load_dotenv

from mcp import ClientSession, types
from mcp.client.streamable_http import streamablehttp_client

"""
This script proves we can reach Tavily's MCP server over Streamable HTTP,
list tools, and run a single search.

Prereqs:
- pip install "mcp" python-dotenv httpx
- .env contains TAVILY_API_KEY
"""

async def main():
    load_dotenv()
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise RuntimeError("Missing TAVILY_API_KEY in environment")

    # Remote Tavily MCP (official hosted endpoint)
    server_url = f"https://mcp.tavily.com/mcp/?tavilyApiKey={api_key}"

    # 1) Connect
    async with streamablehttp_client(server_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 2) List tools
            tools = await session.list_tools()
            tool_names = [t.name for t in tools.tools]
            print("Available tools:", tool_names)

            # Pick the Tavily search tool if present (fallback: first tool)
            search_tool = None
            for name in tool_names:
                if "search" in name.lower():
                    search_tool = name
                    break
            if search_tool is None and tool_names:
                search_tool = tool_names[0]

            if not search_tool:
                raise RuntimeError("No tools exposed by the Tavily MCP server.")

            # 3) Call the search tool once
            # Query keeps it neutral; we'll specialize later for earnings calls.
            query = "latest earnings call transcript for AAPL site:investor.apple.com OR site:fool.com OR site:seekingalpha.com"
            print(f"\nCalling tool: {search_tool}\nQuery: {query}\n")

            result: types.CallToolResult = await session.call_tool(
                search_tool,
                arguments={"query": query, "include_raw_content": False}
            )

            # Print a short, readable result
            # Servers differ; we try both structured and unstructured content.
            if result.structuredContent:
                print("Structured result keys:", list(result.structuredContent.keys()))
                # Try to show top item title/url if present
                top = None
                if isinstance(result.structuredContent, dict):
                    for k in ("results", "data", "items"):
                        if k in result.structuredContent and result.structuredContent[k]:
                            top = result.structuredContent[k][0]
                            break
                if top:
                    print("Top hit (structured):", top)
            else:
                # Unstructured content blocks
                for block in result.content[:3]:
                    if hasattr(block, "text"):
                        print(block.text[:500], "...\n")

if __name__ == "__main__":
    asyncio.run(main())
