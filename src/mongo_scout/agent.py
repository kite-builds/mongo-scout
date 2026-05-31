"""Agent definition: Gemini reasoning + the MongoDB MCP server as tools.

This is the whole point of the project. The agent has no hand-written
database code — every read it performs is a tool call routed through the
MongoDB MCP server, so the surface the LLM is allowed to touch is exactly
what the server exposes (and, with ``--readOnly``, nothing destructive).
"""

from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from mcp import StdioServerParameters

from .config import MCP_SERVER_PACKAGE, Settings

AGENT_NAME = "mongo_scout"

INSTRUCTION = """\
You are Mongo Scout, an operations assistant for a MongoDB deployment.

You answer questions about the data and health of the connected MongoDB
instance by calling the available MongoDB tools — never guess schema,
counts, or contents. Always inspect with a tool first.

Workflow:
1. If you don't yet know which databases/collections exist, list them.
2. Inspect the relevant collection's schema or a small sample before
   making claims about its shape.
3. Prefer aggregations and counts over dumping large result sets; the
   user wants a triage summary, not a raw export.
4. State concrete numbers and collection/field names. If a tool returns
   an error or empty result, say so plainly instead of inventing data.

You operate in read-only mode. If asked to modify data, explain that you
are configured for safe read-only triage and cannot write.
"""


def build_mongodb_toolset(settings: Settings) -> McpToolset:
    """Construct the MongoDB MCP toolset for the given settings.

    The connection is lazy: this only configures *how* to launch the
    stdio MCP server. No subprocess is spawned and no network call is made
    until the agent actually lists or invokes a tool — which is why this
    can be built in unit tests with no live database.
    """
    args = ["-y", MCP_SERVER_PACKAGE]
    env: dict[str, str] = {}
    if settings.read_only:
        args.append("--readOnly")
    if settings.connection_string:
        # Pass via env rather than argv so the URI (which may contain
        # credentials) does not show up in the process list.
        env["MDB_MCP_CONNECTION_STRING"] = settings.connection_string

    server_params = StdioServerParameters(command="npx", args=args, env=env or None)
    return McpToolset(
        connection_params=StdioConnectionParams(server_params=server_params),
    )


def build_agent(settings: Settings) -> LlmAgent:
    """Assemble the Gemini-powered LlmAgent wired to the MongoDB MCP tools."""
    return LlmAgent(
        name=AGENT_NAME,
        model=settings.model,
        instruction=INSTRUCTION,
        description="Read-only natural-language triage agent for MongoDB.",
        tools=[build_mongodb_toolset(settings)],
    )
