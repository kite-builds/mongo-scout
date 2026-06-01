// Boot a seeded, ephemeral MongoDB and hold it open for an external driver.
//
// Used by the Python end-to-end test (tests/test_e2e_agent.py), which needs a
// real MongoDB to point the real mongodb-mcp-server at while it exercises the
// *Gemini+ADK reasoning loop*. Reusing the proven mongodb-memory-server path
// here keeps the mongod lifecycle in one place instead of teaching Python where
// the cached binary lives.
//
// Protocol: prints exactly one line `URI=<connection-string>` once the database
// is seeded and ready, then blocks forever. The parent process reads that line,
// runs its test, and kills this process to tear the database down.
import { MongoMemoryServer } from "mongodb-memory-server";
import { seed } from "./seed.mjs";

const mongod = await MongoMemoryServer.create();
const uri = mongod.getUri();
const facts = await seed(uri);

// Single machine-readable handshake line, then the ground-truth facts on stderr
// so the parent can assert against them without parsing the URI line.
process.stdout.write(`URI=${uri}\n`);
process.stderr.write(`FACTS=${JSON.stringify(facts)}\n`);

const shutdown = async () => {
  try {
    await mongod.stop();
  } finally {
    process.exit(0);
  }
};
process.on("SIGTERM", shutdown);
process.on("SIGINT", shutdown);

// Keep the event loop alive until the parent kills us.
setInterval(() => {}, 1 << 30);
