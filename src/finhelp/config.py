# src/finhelp/config.py
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # Required: your Tavily key
    TAVILY_API_KEY: str = Field(..., description="Tavily API key")
    OPENAI_API_KEY: str = Field(..., description="OpenAI API key")
    # Hosted MCP endpoint; override if needed
    TAVILY_MCP_URL: str = Field(
        default="https://mcp.tavily.com/mcp/?tavilyApiKey={api_key}",
        description="Template URL for Tavily MCP server",
    )

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
