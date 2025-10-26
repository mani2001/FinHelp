# src/finhelp/config.py
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    TAVILY_API_KEY: str = Field(..., description="Tavily API key")
    OPENAI_API_KEY: str = Field(..., description="OpenAI API key")
    MONGODB_URI: str = Field(..., description="MongoDB connection URI")
    JWT_SECRET: str = Field(..., description="JWT secret key")

    TAVILY_MCP_URL: str = Field(
        default="https://mcp.tavily.com/mcp/?tavilyApiKey={api_key}",
        description="Template URL for Tavily MCP server",
    )

    class Config:
        env_file = ".env"  
        extra = "ignore"

settings = Settings()