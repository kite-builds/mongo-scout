"""End-to-end agent-loop test.

Unlike the other test modules (which are fully offline), this one exercises the
*real* ADK runner -> McpToolset -> mongodb-mcp-server -> MongoDB path using a
scripted stand-in for Gemini. It needs Node deps installed (`npm install` in
demo/) so it is skipped automatically when they are absent — keeping the
default `pytest` run green with no setup, while CI that installs the demo deps
gets full loop coverage.

The heavy lifting lives in demo/agent_loop_demo.py; this just runs it and
asserts the loop carried real data end to end.
"""

from __future__ import annotations

import asyncio
import importlib.util
import shutil
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
DEMO = REPO / "demo"


def _deps_present() -> bool:
    return (
        shutil.which("node") is not None
        and (DEMO / "node_modules" / "mongodb-memory-server").exists()
    )


pytestmark = pytest.mark.skipif(
    not _deps_present(),
    reason="needs Node + `npm install` in demo/ (mongodb-memory-server, MCP sdk)",
)


def _load_demo():
    spec = importlib.util.spec_from_file_location("agent_loop_demo", DEMO / "agent_loop_demo.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_agent_loop_carries_live_data():
    demo = _load_demo()
    rc = await asyncio.wait_for(demo.run(), timeout=300)
    assert rc == 0, "agent loop demo reported a failed check"
    # The scripted model must have actually driven tools and read back the
    # live count — proving the loop, not a hardcoded answer.
    assert demo.ScriptedLLM.tool_calls, "no tool calls were issued"
    assert demo.ScriptedLLM.observed_pending == 17, "live pending count did not flow back"
