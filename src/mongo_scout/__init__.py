"""mongo-scout: a Gemini + ADK agent that triages MongoDB via the MongoDB MCP server."""

from .agent import build_agent, build_mongodb_toolset
from .config import Settings, load_settings

__all__ = ["build_agent", "build_mongodb_toolset", "Settings", "load_settings"]
__version__ = "0.1.0"
