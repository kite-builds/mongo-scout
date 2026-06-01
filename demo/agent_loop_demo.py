#!/usr/bin/env python3
"""End-to-end, KEY-FREE proof of the mongo-scout *agent reasoning loop*.

`demo/run.mjs` proves the database layer: the official mongodb-mcp-server,
launched read-only, answers triage questions against a real MongoDB. That is
the *tools*. This script proves the other half — the part a hackathon judge
actually wants to see work — the **Gemini + ADK loop that drives those tools**:

    ADK runner -> LlmAgent -> (model decides) -> McpToolset -> mongodb-mcp-server
              -> tool result -> back into the model -> final natural-language answer

The only thing it does *not* use is a live Gemini key. In its place sits a
`ScriptedLLM` (a real `google.adk.models.BaseLlm`) that plays the exact moves a
competent model makes for the question "how many orders are stuck pending?":
list the collections, count `orders` where `status="pending"`, then answer.

Crucially the final number is **not hardcoded** — `ScriptedLLM` reads it out of
the live `FunctionResponse` the MCP server returned, so a green run proves the
whole loop carried real data model->tool->model->answer. Swap `ScriptedLLM` for
`"gemini-2.0-flash"` + a key and the identical wiring runs against Gemini.

Run:  python demo/agent_loop_demo.py        (needs `npm install` in demo/ first)
Exit: 0 only if the agent answered from live tool output with the right number.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from pathlib import Path
from typing import AsyncGenerator

# Make the package importable whether run from repo root or demo/.
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from google.adk.agents import LlmAgent  # noqa: E402
from google.adk.models.base_llm import BaseLlm  # noqa: E402
from google.adk.models.llm_request import LlmRequest  # noqa: E402
from google.adk.models.llm_response import LlmResponse  # noqa: E402
from google.adk.runners import InMemoryRunner  # noqa: E402
from google.genai import types  # noqa: E402

from mongo_scout.agent import AGENT_NAME, INSTRUCTION, build_mongodb_toolset  # noqa: E402
from mongo_scout.config import load_settings  # noqa: E402

DB = "shop"
APP = "mongo-scout-loop-demo"
USER = "operator"


def _log(*a: object) -> None:
    print(*a, flush=True)


def _hr() -> None:
    _log("─" * 72)


# --------------------------------------------------------------------------- #
# The scripted stand-in for Gemini.                                           #
# --------------------------------------------------------------------------- #
class ScriptedLLM(BaseLlm):
    """A deterministic `BaseLlm` that drives the MongoDB tools by hand.

    It inspects the conversation so far (which tools it has already called and
    what they returned) and emits the next function call — or, once it has the
    data, a final answer whose number is extracted from the live tool result.
    This is a faithful stand-in for a model doing tool-use: ADK cannot tell the
    difference, so the runner/toolset path exercised is exactly production's.
    """

    # Recorded for the test harness to assert on after the run.
    tool_calls: list[str] = []
    observed_pending: int | None = None

    def __init__(self) -> None:
        super().__init__(model="scripted-llm")

    @staticmethod
    def _available(req: LlmRequest) -> list[str]:
        names: list[str] = []
        for tool in (req.config.tools or []):
            for decl in (getattr(tool, "function_declarations", None) or []):
                if decl.name:
                    names.append(decl.name)
        return names

    @staticmethod
    def _pick(names: list[str], *must: str) -> str | None:
        for n in names:
            low = n.lower()
            if all(m in low for m in must):
                return n
        return None

    @staticmethod
    def _history(req: LlmRequest):
        calls: list[str] = []
        responses: dict[str, object] = {}
        for content in (req.contents or []):
            for part in (content.parts or []):
                if part.function_call and part.function_call.name:
                    calls.append(part.function_call.name)
                if part.function_response and part.function_response.name:
                    responses[part.function_response.name] = part.function_response.response
        return calls, responses

    @staticmethod
    def _extract_int(payload: object) -> int | None:
        # MCP tool results come back as a dict; the count tool says
        # "Found 17 documents ...". Scan the whole stringified payload.
        m = re.search(r"-?\d[\d,]*", json.dumps(payload, default=str))
        return int(m.group(0).replace(",", "")) if m else None

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        names = self._available(llm_request)
        called, responses = self._history(llm_request)

        list_tool = self._pick(names, "list", "collection") or "list-collections"
        count_tool = self._pick(names, "count") or "count"

        def call(name: str, args: dict) -> LlmResponse:
            ScriptedLLM.tool_calls.append(name)
            return LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[types.Part(function_call=types.FunctionCall(name=name, args=args))],
                )
            )

        # Step 1: discover the collections (the model never guesses schema).
        if list_tool not in called:
            yield call(list_tool, {"database": DB})
            return

        # Step 2: count the stuck orders.
        if count_tool not in called:
            yield call(
                count_tool,
                {"database": DB, "collection": "orders", "query": {"status": "pending"}},
            )
            return

        # Step 3: answer using the number the live tool actually returned.
        pending = self._extract_int(responses.get(count_tool))
        ScriptedLLM.observed_pending = pending
        answer = (
            f"There are {pending} orders currently stuck in 'pending' in the "
            f"'{DB}' database. I determined this by listing the collections and "
            f"then running a read-only count on orders where status='pending' "
            f"via the MongoDB MCP server."
        )
        yield LlmResponse(
            content=types.Content(role="model", parts=[types.Part(text=answer)])
        )


# --------------------------------------------------------------------------- #
# Harness: boot a real mongod, run the loop, assert it carried real data.     #
# --------------------------------------------------------------------------- #
async def _boot_mongod() -> tuple[asyncio.subprocess.Process, str, dict]:
    """Start the seeded ephemeral MongoDB via the Node bootstrapper."""
    proc = await asyncio.create_subprocess_exec(
        "node", "boot_mongod.mjs",
        cwd=str(Path(__file__).resolve().parent),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    uri = ""
    while True:
        line = await asyncio.wait_for(proc.stdout.readline(), timeout=120)
        if not line:
            err = (await proc.stderr.read()).decode()
            raise RuntimeError(f"mongod bootstrap exited early:\n{err}")
        text = line.decode().strip()
        if text.startswith("URI="):
            uri = text[len("URI="):]
            break
    facts_line = await asyncio.wait_for(proc.stderr.readline(), timeout=30)
    facts = json.loads(facts_line.decode().split("FACTS=", 1)[1])
    return proc, uri, facts


async def run() -> int:
    _log("mongo-scout — end-to-end AGENT LOOP demo (no Gemini key, no cloud account)\n")

    _log("1/4  Booting a seeded ephemeral MongoDB (mongodb-memory-server)…")
    proc, uri, facts = await _boot_mongod()
    _log(f"     up at {uri}")
    _log(f'     seeded db "{facts["db"]}": {json.dumps(facts["counts"])}; '
         f'ground-truth pending orders = {facts["pendingOrders"]}')

    ok = False
    try:
        _log("2/4  Building the REAL ADK agent — scripted model + MongoDB MCP toolset…")
        settings = load_settings(env={"MDB_MCP_CONNECTION_STRING": uri, "MONGO_SCOUT_READONLY": "true"})
        ScriptedLLM.tool_calls = []
        ScriptedLLM.observed_pending = None
        agent = LlmAgent(
            name=AGENT_NAME,
            model=ScriptedLLM(),
            instruction=INSTRUCTION,
            description="Read-only triage agent (scripted-LLM e2e harness).",
            tools=[build_mongodb_toolset(settings)],
        )
        _log(f"     agent '{agent.name}' built with {len(agent.tools)} toolset(s); "
             f"--readOnly={settings.read_only}")

        _log("3/4  Running the loop on: \"How many orders are stuck in pending right now?\"")
        runner = InMemoryRunner(agent=agent, app_name=APP)
        await runner.session_service.create_session(app_name=APP, user_id=USER, session_id="cli")
        question = types.Content(
            role="user",
            parts=[types.Part(text="How many orders are stuck in pending right now?")],
        )
        final = ""
        async for event in runner.run_async(user_id=USER, session_id="cli", new_message=question):
            for part in (event.content.parts if event.content else []):
                if part.function_call:
                    _log(f"  → model calls tool: {part.function_call.name}"
                         f"({json.dumps(dict(part.function_call.args or {}))})")
                if part.function_response:
                    payload = json.dumps(part.function_response.response, default=str)
                    _log(f"  ← tool returned: {payload[:160]}"
                         + ("…" if len(payload) > 160 else ""))
            if event.is_final_response() and event.content and event.content.parts:
                final = "".join(p.text or "" for p in event.content.parts).strip()

        _log("\n  Agent's final answer:")
        _log(f"    {final}")

        _hr()
        _log("4/4  Verifying the loop carried REAL data (not a hardcoded number)…")
        checks = []

        def record(label: str, passed: bool, detail: str = "") -> None:
            checks.append(passed)
            _log(f"  {'✔' if passed else '✘'} {label}" + (f" — {detail}" if detail else ""))

        record("the model issued live tool calls through ADK",
               len(ScriptedLLM.tool_calls) >= 2,
               f"calls = {ScriptedLLM.tool_calls}")
        record("the count read back from the MCP server equals seeded ground truth",
               ScriptedLLM.observed_pending == facts["pendingOrders"],
               f"observed {ScriptedLLM.observed_pending}, seeded {facts['pendingOrders']}")
        record("the final natural-language answer contains that live number",
               str(facts["pendingOrders"]) in final,
               f"answer cites {facts['pendingOrders']}")

        ok = all(checks)
        _hr()
        passed = sum(1 for c in checks if c)
        _log(f"\nRESULT: {passed}/{len(checks)} checks green — the full Gemini-shaped "
             f"agent loop ran against a real MongoDB with no key.")
        if ok:
            _log("Swap ScriptedLLM for 'gemini-2.0-flash' + GEMINI_API_KEY and the "
                 "identical wiring runs on Gemini.")
        else:
            _log("Some checks failed — see transcript above.")
    finally:
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=15)
        except asyncio.TimeoutError:
            proc.kill()

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
