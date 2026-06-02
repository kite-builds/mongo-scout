# mongo-scout — Devpost submission package

Ready-to-paste content for the **Google Cloud Rapid Agent Hackathon**
(MongoDB track). Everything here is backed by code in this repo; nothing is
aspirational. The demo video referenced below is
[`demo/media/mongo-scout-demo.mp4`](./demo/media/mongo-scout-demo.mp4)
(GIF preview in the [README](./README.md#demo)).

> **One remaining manual step (cannot be automated pseudonymously):** upload
> `demo/media/mongo-scout-demo.mp4` to YouTube/Vimeo and paste the URL into the
> Devpost "Video" field, then submit the form. Everything else below is final.

---

## Project name
mongo-scout

## Tagline (≤200 chars)
A read-only natural-language triage agent for MongoDB. Ask production data plain
questions; every read is a tool call through the official MongoDB MCP server,
launched `--readOnly` so it can't mutate anything.

## Elevator pitch
On-call engineers and analysts constantly need to know "what does the data say
*right now*?" — counts, growth, stuck records, schema drift — without writing a
one-off aggregation each time. mongo-scout turns those into plain questions. It
runs on **Gemini + Google ADK** and touches the database **only** through the
**official MongoDB MCP server**, launched `--readOnly`. There is zero
hand-written DB code: the model's entire database surface *is* the MCP server,
and it is safe by construction — it physically cannot drop or mutate data.

## Which track
MongoDB partner track.

## What it does
- Accepts a plain-English question about a live MongoDB deployment.
- The Gemini agent plans, then answers using only MCP tool calls
  (`list-collections`, `count`, `aggregate`, `collection-schema`, `find`, …).
- Returns real numbers derived from live tool output — never guessed.
- Cannot mutate: launched with `--readOnly`, the server exposes **no**
  write/delete/drop tools, so prompt-injected "delete everything" requests have
  no tool to call.

## How we built it
- **Agent:** `google.adk.agents.LlmAgent` running `gemini-2.0-flash`
  (`src/mongo_scout/agent.py`).
- **Tools:** ADK `McpToolset` launches the official `mongodb-mcp-server` over
  stdio with `--readOnly`; the connection string is passed via the server's
  **environment, not argv**, so credentials never appear in the process list.
- **No DB code:** every read is a model-issued MCP tool call. The repo contains
  no hand-written queries.
- **Reproducibility:** two key-free, account-free proofs under `demo/` boot a
  real ephemeral MongoDB (`mongodb-memory-server`) and drive the real MCP
  server — `npm run demo` (database layer, 5/5 checks) and `npm run loop` (the
  full ADK reasoning loop, model→tool→model→answer, 3/3 checks).

## Challenges we ran into
- **Untrusted-data handling.** The MongoDB MCP server wraps every row of DB
  output in an explicit prompt-injection guard (`<untrusted-user-data-…>`
  fences). Designing the agent to treat tool output as data, not instructions,
  is core to keeping a data-reading agent safe — the demo surfaces these fences
  so reviewers can see the boundary the model must respect.
- **Provable safety.** Rather than *prompting* the model to be read-only, we
  enforce it at the tool layer: `--readOnly` removes the write tools entirely,
  so safety doesn't depend on the model behaving.
- **Reviewer reproducibility without secrets.** We made both proofs run with no
  Gemini key and no Atlas account by swapping in an ephemeral mongod and (for
  the loop) a scripted LLM with identical wiring.

## Accomplishments we're proud of
- A genuinely **safe-by-construction** data agent — not "please don't delete",
  but "there is no delete tool".
- An **end-to-end proof anyone can run in ~30s** with a single command and no
  credentials, including the full Gemini-shaped ADK loop.

## What we learned
MCP turns "give the model database access" into a bounded, auditable capability:
the exact tool surface is visible, launch flags constrain it, and untrusted rows
arrive pre-fenced. That combination is what makes an autonomous DB agent
defensible in production.

## What's next
- Read-replica connection-string presets and per-collection allowlists.
- A "diff since yesterday" mode for drift/anomaly triage.
- Optional Slack surface so on-call can ask in-channel.

## Tech stack
Python · Google ADK · Gemini (`gemini-2.0-flash`) · Model Context Protocol ·
official `mongodb-mcp-server` · MongoDB · Node (demo harness:
`mongodb-memory-server`).

## Try it out (links)
- Repo: https://github.com/kite-builds/mongo-scout
- Quick start & rules mapping: [`HACKATHON.md`](./HACKATHON.md)
- One-command demo: `cd demo && npm install && npm run demo`

## Judge quick-start (copy/paste)
```bash
git clone https://github.com/kite-builds/mongo-scout && cd mongo-scout
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q                       # offline, green with no key and no MongoDB
mongo-scout --check             # builds the live agent + MCP toolset, no network
cd demo && npm install && npm run demo   # real MongoDB + real MCP server, 5/5 checks
npm run loop                    # full ADK reasoning loop, 3/3 checks (no Gemini key)
```

## Demo video
- File in repo: [`demo/media/mongo-scout-demo.mp4`](./demo/media/mongo-scout-demo.mp4)
- GIF preview: [`demo/media/mongo-scout-demo.gif`](./demo/media/mongo-scout-demo.gif)
- Source cast: [`demo/media/demo.cast`](./demo/media/demo.cast) (asciinema v2)
- Regenerate: `bash demo/record/make_video.sh`
- **TODO before submit:** host the MP4 on YouTube/Vimeo and paste the URL into
  Devpost. (Pseudonymous account creation / video hosting is the one step left
  for the operator.)
