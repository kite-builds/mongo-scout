"""Agent-construction tests.

These run fully offline: building the agent and the MCP toolset only
*configures* how to launch the stdio server — no subprocess is spawned and
no Gemini call is made until a tool is actually invoked. That is exactly
the property we assert here, so CI needs neither a Gemini key nor a Mongo.
"""

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset

from mongo_scout.agent import AGENT_NAME, build_agent, build_mongodb_toolset
from mongo_scout.config import MCP_SERVER_PACKAGE, load_settings


def _stdio_args(toolset: McpToolset) -> list[str]:
    return toolset._connection_params.server_params.args


def test_build_agent_offline():
    agent = build_agent(load_settings(env={}))
    assert isinstance(agent, LlmAgent)
    assert agent.name == AGENT_NAME
    assert agent.model == "gemini-2.0-flash"
    assert len(agent.tools) == 1
    assert isinstance(agent.tools[0], McpToolset)


def test_toolset_launches_mongodb_mcp_server():
    toolset = build_mongodb_toolset(load_settings(env={}))
    params = toolset._connection_params.server_params
    assert params.command == "npx"
    assert MCP_SERVER_PACKAGE in params.args


def test_readonly_flag_passed_when_enabled():
    toolset = build_mongodb_toolset(load_settings(env={"MONGO_SCOUT_READONLY": "true"}))
    assert "--readOnly" in _stdio_args(toolset)


def test_readonly_flag_absent_when_disabled():
    toolset = build_mongodb_toolset(load_settings(env={"MONGO_SCOUT_READONLY": "false"}))
    assert "--readOnly" not in _stdio_args(toolset)


def test_connection_string_passed_via_env_not_argv():
    uri = "mongodb+srv://u:p@cluster.example.net/"
    toolset = build_mongodb_toolset(
        load_settings(env={"MDB_MCP_CONNECTION_STRING": uri})
    )
    params = toolset._connection_params.server_params
    # Credentials must not appear in argv (visible in `ps`); only in env.
    assert uri not in " ".join(params.args)
    assert params.env["MDB_MCP_CONNECTION_STRING"] == uri
