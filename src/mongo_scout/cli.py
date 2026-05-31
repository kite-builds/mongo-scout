"""Command-line entry point.

Usage:
    mongo-scout --check                 # offline: build the agent, print wiring
    mongo-scout "how many users signed up in the last 7 days?"

A live query needs GEMINI_API_KEY and MDB_MCP_CONNECTION_STRING in the
environment; ``--check`` needs neither and is what CI runs.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from google.adk.runners import InMemoryRunner
from google.genai import types

from .agent import AGENT_NAME, build_agent
from .config import load_settings

APP_NAME = "mongo-scout"
USER_ID = "operator"


def _print_wiring(settings) -> None:
    print("mongo-scout configuration")
    print(f"  model            : {settings.model}")
    print(f"  read_only        : {settings.read_only}")
    print(f"  live MongoDB set : {settings.has_live_db}")
    agent = build_agent(settings)
    print(f"  agent            : {agent.name} with {len(agent.tools)} toolset(s)")
    print("OK: agent builds. Set GEMINI_API_KEY + MDB_MCP_CONNECTION_STRING to run a query.")


async def _run_query(settings, query: str) -> int:
    agent = build_agent(settings)
    runner = InMemoryRunner(agent=agent, app_name=APP_NAME)
    await runner.session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id="cli"
    )
    message = types.Content(role="user", parts=[types.Part(text=query)])
    final = ""
    async for event in runner.run_async(
        user_id=USER_ID, session_id="cli", new_message=message
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final = "".join(p.text or "" for p in event.content.parts)
    print(final.strip() or "(no response)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mongo-scout", description=__doc__)
    parser.add_argument("query", nargs="?", help="natural-language question about the MongoDB")
    parser.add_argument(
        "--check", action="store_true", help="build the agent and print wiring, no model call"
    )
    args = parser.parse_args(argv)
    settings = load_settings()

    if args.check or not args.query:
        _print_wiring(settings)
        if not args.query:
            return 0
    if not settings.has_live_db:
        print(
            "error: MDB_MCP_CONNECTION_STRING is not set — cannot run a live query.",
            file=sys.stderr,
        )
        return 2
    return asyncio.run(_run_query(settings, args.query))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
