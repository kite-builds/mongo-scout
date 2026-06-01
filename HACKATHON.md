# Google Cloud Rapid Agent Hackathon — submission notes

**Track:** MongoDB
**Project:** mongo-scout — a read-only natural-language triage agent for MongoDB.

## How this meets the requirements

The [official rules](https://rapid-agent.devpost.com/rules) require a project
that is (1) **newly created during the contest period**, (2) **powered by
Gemini + Google Cloud Agent Builder/ADK**, and (3) **integrates a partner's
MCP server**. mongo-scout satisfies all three:

1. **New work.** This repository was created from scratch for this hackathon
   (contest period May 1 – June 11, 2026). It is not an extension of any
   prior project.
2. **Gemini + ADK.** The agent is a `google.adk.agents.LlmAgent` running a
   Gemini model (`gemini-2.0-flash` by default). See `src/mongo_scout/agent.py`.
3. **Partner MCP server.** Every database operation is a tool call routed
   through the official **MongoDB MCP server** (`mongodb-mcp-server`), launched
   over stdio by ADK's `McpToolset`. There is zero hand-written DB code — the
   model's entire database surface *is* the MCP server.

## The real challenge it solves

On-call engineers and analysts constantly need to answer "what does the data
say right now?" against a production MongoDB — counts, growth, stuck records,
schema drift — without writing a one-off aggregation pipeline each time. mongo-scout
turns those into plain questions while staying **safe by construction**: the
MCP server is launched with `--readOnly`, so the agent cannot mutate or drop
anything even if asked. The connection string is passed via the server's
environment, not argv, so credentials never appear in the process list.

## Judge quick-start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q                 # offline, green with no Gemini key and no MongoDB
mongo-scout --check       # builds the live agent + MongoDB MCP toolset, no network
```

For a live demo, set `GEMINI_API_KEY` (free from AI Studio) and
`MDB_MCP_CONNECTION_STRING` (Atlas free tier works), then:

```bash
mongo-scout "list the databases and which collection has the most documents"
```

### Reproducible end-to-end proof (no key, no account)

For reviewers who don't want to provision Gemini + Atlas, [`demo/`](./demo)
proves the MCP integration works against a **real** MongoDB with one command:

```bash
cd demo && npm install && npm run demo
```

It launches an ephemeral `mongod` (`mongodb-memory-server`), seeds a realistic
ops dataset, and drives the **real `mongodb-mcp-server@latest`** with the exact
`--readOnly` launch parameters from `build_mongodb_toolset()` — answering five
triage questions purely from live tool calls and asserting each against the
seeded ground truth. A captured run is at [`demo/transcript.txt`](./demo/transcript.txt).
This is the same tool surface Gemini drives in production; the demo just swaps
the LLM client for a deterministic harness so it needs no credentials.

## Status checklist (for the Devpost form)

- [x] New repo, MIT-licensed, license visible at repo root
- [x] Gemini + ADK agent, MongoDB MCP server integrated, read-only by default
- [x] Offline test suite green; `--check` smoke path
- [x] Reproducible end-to-end MCP proof against a real MongoDB (`demo/`, no key/account)
- [ ] ~3-minute demo video (record `npm run demo` + a live Gemini query)
- [ ] Hosted project URL
- [ ] Devpost submission form (MongoDB track)
```
