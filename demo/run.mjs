// End-to-end, KEY-FREE demo of the mongo-scout database layer.
//
// What it proves: the project's central claim — "the agent has no hand-written
// database code; every read is a tool call through the official MongoDB MCP
// server, launched in --readOnly mode" — actually works against a REAL MongoDB.
//
// It needs no Gemini key and no cloud account: it spins up an ephemeral mongod
// via mongodb-memory-server, seeds a realistic ops dataset, then drives the
// real `mongodb-mcp-server` over the Model Context Protocol exactly as ADK's
// McpToolset does in src/mongo_scout/agent.py. The transcript it prints is the
// same tool surface Gemini sees at runtime.
//
//   node run.mjs            # human-readable transcript
//
// Exit code 0 only if every triage question was answered from live tool output.
import { MongoMemoryServer } from "mongodb-memory-server";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { seed } from "./seed.mjs";

const log = (...a) => console.log(...a);
const hr = () => log("─".repeat(72));

// Pull the text payload out of an MCP tool result.
function text(res) {
  if (res?.isError) return `ERROR: ${(res.content ?? []).map((c) => c.text).join(" ")}`;
  return (res?.content ?? []).map((c) => c.text ?? "").join("\n").trim();
}

async function main() {
  log("mongo-scout — end-to-end MCP demo (no Gemini key, no cloud account)\n");

  log("1/4  Starting an ephemeral MongoDB (mongodb-memory-server)…");
  const mongod = await MongoMemoryServer.create();
  const uri = mongod.getUri();
  log(`     up at ${uri}`);

  log("2/4  Seeding a realistic operations dataset…");
  const facts = await seed(uri);
  log(`     db "${facts.db}": ${JSON.stringify(facts.counts)}`);

  log("3/4  Launching the REAL mongodb-mcp-server over stdio (--readOnly)…");
  // Identical wiring to ADK's StdioServerParameters in agent.py: command npx,
  // package mongodb-mcp-server, --readOnly, connection string via env not argv.
  const transport = new StdioClientTransport({
    command: "npx",
    args: ["-y", "mongodb-mcp-server@latest", "--readOnly"],
    env: { ...process.env, MDB_MCP_CONNECTION_STRING: uri },
  });
  const client = new Client({ name: "mongo-scout-demo", version: "0.1.0" }, { capabilities: {} });
  await client.connect(transport);

  const { tools } = await client.listTools();
  const names = tools.map((t) => t.name);
  log(`     connected. server exposes ${tools.length} tools: ${names.join(", ")}`);
  const has = (n) => names.includes(n);

  // Helper: print the call, run it, print the live result. Never throws —
  // a tool that errors still belongs in the transcript, and one bad call
  // must not tear down the stdio transport mid-write.
  async function call(name, args) {
    log(`\n  → tool: ${name}(${JSON.stringify(args)})`);
    try {
      const res = await client.callTool({ name, arguments: args });
      const out = text(res);
      log(`  ← ${out.replace(/\n/g, "\n     ")}`);
      return out;
    } catch (e) {
      const out = `ERROR: ${e?.message ?? e}`;
      log(`  ← ${out}`);
      return out;
    }
  }

  const checks = [];
  const record = (label, ok, detail) => {
    checks.push({ label, ok });
    log(`  ${ok ? "✔" : "✘"} ${label}${detail ? ` — ${detail}` : ""}`);
  };

  hr();
  log('Q1. "What collections exist and which one holds the most documents?"');
  const cols = has("list-collections") ? await call("list-collections", { database: facts.db }) : "";
  const sizes = {};
  for (const c of ["users", "orders", "events"]) {
    if (has("count")) {
      const out = await call("count", { database: facts.db, collection: c, query: {} });
      const m = out.match(/-?\d[\d,]*/);
      if (m) sizes[c] = Number(m[0].replace(/,/g, ""));
    }
  }
  const biggest = Object.entries(sizes).sort((a, b) => b[1] - a[1])[0]?.[0];
  record("collections listed and counted via live tool calls",
    cols.includes("orders") && Object.keys(sizes).length === 3,
    `biggest = ${biggest} (${JSON.stringify(sizes)})`);

  hr();
  log('Q2. "How many orders are stuck in pending right now?"');
  let pending = null;
  if (has("count")) {
    const out = await call("count", { database: facts.db, collection: "orders", query: { status: "pending" } });
    const m = out.match(/-?\d[\d,]*/);
    if (m) pending = Number(m[0].replace(/,/g, ""));
  }
  record("pending-order count matches the seeded ground truth",
    pending === facts.pendingOrders, `tool says ${pending}, seeded ${facts.pendingOrders}`);

  hr();
  log('Q3. "Break orders down by status." (aggregation, not a raw dump)');
  let statusOk = false;
  if (has("aggregate")) {
    const out = await call("aggregate", {
      database: facts.db,
      collection: "orders",
      pipeline: [{ $group: { _id: "$status", n: { $sum: 1 } } }, { $sort: { n: -1 } }],
    });
    statusOk = out.includes("pending") && out.includes("paid");
  }
  record("status breakdown returned by a real $group aggregation", statusOk);

  hr();
  log('Q4. "Inspect the shape of orders before making claims about it."');
  let schemaOk = false;
  if (has("collection-schema")) {
    const out = await call("collection-schema", { database: facts.db, collection: "orders" });
    // The model is instructed to inspect schema first; prove the tool returns
    // the real fields (status, amount, userId) rather than the agent guessing.
    schemaOk = /status/.test(out) && /amount/.test(out) && /userId/.test(out);
  }
  record("real collection schema (status/amount/userId) returned by a tool", schemaOk,
    "the agent inspects shape instead of guessing");

  hr();
  log('Q5. "Prove read-only: can the agent delete anything?"');
  let writeBlocked = false;
  const writeTool = names.find((n) => /delete|drop|update|insert/.test(n));
  if (writeTool) {
    record(`a write tool (${writeTool}) is exposed but should be refused`, false);
  } else {
    writeBlocked = true;
    record("server started with --readOnly exposes NO write/delete/drop tools", true,
      "the agent physically cannot mutate data");
  }

  await client.close();
  await mongod.stop();

  hr();
  const passed = checks.filter((c) => c.ok).length;
  log(`\nRESULT: ${passed}/${checks.length} triage checks answered from live MCP tool calls.`);
  if (passed !== checks.length) {
    log("Some checks did not pass — see transcript above.");
    process.exit(1);
  }
  log("All checks green. This is the exact tool surface Gemini drives in production.");
}

main().catch((e) => {
  console.error("\nDEMO FAILED:", e?.message ?? e);
  process.exit(1);
});
