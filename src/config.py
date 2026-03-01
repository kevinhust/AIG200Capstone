import os
from pathlib import Path
from typing import List, Optional
from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict


class MCPServerConfig(BaseSettings):
    """Configuration for a single MCP server."""

    name: str = Field(description="Unique name for the MCP server")
    transport: str = Field(
        default="stdio", description="Transport type: stdio, http, sse"
    )
    command: Optional[str] = Field(
        default=None, description="Command to run for stdio transport"
    )
    args: List[str] = Field(
        default_factory=list, description="Arguments for the command"
    )
    url: Optional[str] = Field(default=None, description="URL for http/sse transport")
    env: dict = Field(
        default_factory=dict, description="Environment variables for the server"
    )
    enabled: bool = Field(default=True, description="Whether this server is enabled")

    model_config = SettingsConfigDict(extra="ignore")


class Settings(BaseSettings):
    """Application settings managed by Pydantic."""

    # Google GenAI Configuration
    GOOGLE_API_KEY: str = Field(
        default="",
        validation_alias=AliasChoices("GOOGLE_API_KEY", "GEMINI_API_KEY"),
        description="Google API Key for Gemini. Supports both GOOGLE_API_KEY and GEMINI_API_KEY env vars."
    )
    # Default to Flash to avoid free-tier Pro quota errors; override via env if needed.
    GEMINI_MODEL_NAME: str = "gemini-2.5-flash"

    # Agent Configuration
    AGENT_NAME: str = "AntigravityAgent"
    DEBUG_MODE: bool = False

    # External LLM (OpenAI-compatible) Configuration
    OPENAI_BASE_URL: str = Field(
        default="",
        description="Base URL for OpenAI-compatible API (e.g., https://api.openai.com/v1 or http://localhost:11434/v1)",
    )
    OPENAI_API_KEY: str = Field(
        default="",
        description="API key for OpenAI-compatible endpoint. Leave blank if not required.",
    )
    OPENAI_MODEL: str = Field(
        default="gpt-4o-mini",
        description="Default model name for OpenAI-compatible chat completions.",
    )

    # Z.AI Configuration (for Coder/Reviewer)
    ZAI_BASE_URL: str = Field(default="", description="Base URL for Z.AI API")
    ZAI_API_KEY: str = Field(default="", description="API key for Z.AI")
    
    # xAI Configuration (for Researcher)
    XAI_BASE_URL: str = Field(default="", description="Base URL for xAI API")
    XAI_API_KEY: str = Field(default="", description="API key for xAI")
    XAI_MODEL: str = Field(default="grok-4-1-fast-reasoning", description="Model name for xAI")

    # Memory Configuration
    MEMORY_FILE: str = "agent_memory.json"

    # MCP Configuration
    MCP_ENABLED: bool = Field(default=False, description="Enable MCP integration")
    MCP_SERVERS_CONFIG: str = Field(
        default="mcp_servers.json", description="Path to MCP servers configuration file"
    )
    MCP_CONNECTION_TIMEOUT: int = Field(
        default=30, description="Timeout in seconds for MCP server connections"
    )
    MCP_TOOL_PREFIX: str = Field(
        default="mcp_", description="Prefix for MCP tool names to avoid conflicts"
    )

    # Wger API Configuration
    WGER_API_BASE_URL: str = "https://wger.de/api/v2/"

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Global settings instance
settings = Settings()
