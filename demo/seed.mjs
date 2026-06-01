// Seed a small but realistic operations dataset into a MongoDB so the demo
// has something worth triaging: users with signup timestamps, orders with a
// status field (some stuck in `pending`), and an events collection that is
// missing an obvious index. Returns the names so the runner can assert on them.
import { MongoClient } from "mongodb";

const DB = "shop";

// Deterministic "now" so the transcript is stable across runs.
const NOW = new Date("2026-06-01T00:00:00Z");
const daysAgo = (d) => new Date(NOW.getTime() - d * 24 * 60 * 60 * 1000);

export async function seed(uri) {
  const client = new MongoClient(uri);
  await client.connect();
  const db = client.db(DB);

  const users = Array.from({ length: 40 }, (_, i) => ({
    _id: i + 1,
    email: `user${i + 1}@example.com`,
    // 12 of the 40 signed up within the last 7 days.
    createdAt: daysAgo(i < 12 ? (i % 7) : 8 + (i % 60)),
    plan: i % 5 === 0 ? "pro" : "free",
  }));

  // No "pending" in the rotation, so exactly the first 17 are pending — the
  // kind of stuck-record pileup on-call wants surfaced, with a clean count.
  const statuses = ["paid", "paid", "paid", "shipped", "refunded", "paid", "shipped"];
  const orders = Array.from({ length: 120 }, (_, i) => ({
    _id: i + 1,
    userId: (i % 40) + 1,
    amount: 50 + (i % 20) * 7,
    status: i < 17 ? "pending" : statuses[i % statuses.length],
    createdAt: daysAgo(i % 30),
  }));

  // A high-write collection that an analyst would expect to be queried by
  // `name` + `createdAt` but which has no supporting index — a real triage find.
  const events = Array.from({ length: 300 }, (_, i) => ({
    _id: i + 1,
    name: ["page_view", "add_to_cart", "checkout", "login"][i % 4],
    userId: (i % 40) + 1,
    createdAt: daysAgo(i % 14),
  }));

  await db.collection("users").insertMany(users);
  await db.collection("orders").insertMany(orders);
  await db.collection("events").insertMany(events);

  // Give `users` a sensible index so the contrast with `events` (none) is real.
  await db.collection("users").createIndex({ createdAt: -1 });

  await client.close();

  return {
    db: DB,
    counts: { users: users.length, orders: orders.length, events: events.length },
    pendingOrders: orders.filter((o) => o.status === "pending").length,
    usersLast7d: users.filter((u) => u.createdAt >= daysAgo(7)).length,
  };
}
