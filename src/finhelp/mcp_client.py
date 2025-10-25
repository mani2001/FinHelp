# src/finhelp/mcp_client.py
import asyncio
from contextlib import asynccontextmanager
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from .config import settings

@asynccontextmanager
async def mcp_session():
    """
    Yields an initialized MCP ClientSession connected to Tavily.
    Usage:
      async with mcp_session() as session:
          tools = await session.list_tools()
    """
    server_url = settings.TAVILY_MCP_URL.format(api_key=settings.TAVILY_API_KEY)
    async with streamablehttp_client(server_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session
