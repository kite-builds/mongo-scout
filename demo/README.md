# mongo-scout — end-to-end demo (no key, no cloud account)

This proves the project's central claim is real, not aspirational:

> mongo-scout has **no hand-written database code**. Every read is a tool call
> routed through the **official MongoDB MCP server**, launched in `--readOnly`
> mode — so the surface the Gemini agent can touch is exactly what the MCP
> server exposes, and nothing destructive.

The Python agent (`src/mongo_scout/agent.py`) wires Gemini to that MCP server
via ADK's `McpToolset`. This demo exercises the **same MCP server with the same
launch parameters**, but drives it from a plain MCP client so it needs **no
Gemini key and no MongoDB account**. The tool transcript it prints is the exact
surface Gemini sees at runtime.

## Run it

```bash
cd demo
npm install
npm run demo
```

`npm run demo`:

1. starts an **ephemeral real MongoDB** via `mongodb-memory-server` (downloads a
   `mongod` binary the first time — no install, no account),
2. seeds a realistic ops dataset (40 users, 120 orders with 17 stuck in
   `pending`, 300 events),
3. launches the **real `mongodb-mcp-server@latest`** over stdio with
   `--readOnly` and the connection string passed via env (not argv) — identical
   to `build_mongodb_toolset()` in the agent,
4. answers five triage questions purely from live MCP tool calls and asserts
   each result against the seeded ground truth,
5. tears everything down. Exit code `0` only if all five checks pass.

## What each check proves

| Q | Triage question | MCP tool(s) | Proves |
|---|---|---|---|
| 1 | Which collection holds the most documents? | `list-collections`, `count` | discovers + counts live, no guessing |
| 2 | How many orders are stuck in `pending`? | `count` with a filter | exact match to seeded ground truth (17) |
| 3 | Break orders down by status | `aggregate` (`$group`) | prefers aggregation over raw dumps |
| 4 | Inspect the shape of `orders` first | `collection-schema` | inspects schema before claiming |
| 5 | Can the agent delete anything? | tool enumeration | `--readOnly` exposes **zero** write/drop tools |

A captured run is checked in at [`transcript.txt`](./transcript.txt) so reviewers
can see the live output (including the MCP server's prompt-injection guard
wrapping untrusted DB content) without running anything.

> Note: `mongodb-mcp-server`'s `collection-indexes` tool calls an Atlas-only
> `$listSearchIndexes` stage, so index triage is an Atlas-only capability and is
> intentionally not part of this local, account-free demo.
