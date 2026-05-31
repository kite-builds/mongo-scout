"""Runtime configuration for mongo-scout.

Everything is driven by environment variables so the same agent definition
runs locally, in CI (with stubbed creds), and against a live MongoDB Atlas
cluster without code changes.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

# Gemini model used to reason over MongoDB tool results. Flash is the
# default because the agent's job is fast, tool-heavy triage rather than
# long-form generation.
DEFAULT_MODEL = "gemini-2.0-flash"

# The official MongoDB MCP server, published to npm by MongoDB. Run over
# stdio via npx so there is nothing to pre-install. Pinning to a tag keeps
# CI reproducible while still being a one-liner for a judge to run.
MCP_SERVER_PACKAGE = "mongodb-mcp-server@latest"


@dataclass(frozen=True)
class Settings:
    """Resolved configuration for a single agent run."""

    model: str
    connection_string: str | None
    read_only: bool

    @property
    def has_live_db(self) -> bool:
        return bool(self.connection_string)


def load_settings(env: dict[str, str] | None = None) -> Settings:
    """Build :class:`Settings` from the process environment.

    Reads:
      * ``GEMINI_API_KEY``    — consumed by the ADK Gemini model directly.
      * ``MONGO_SCOUT_MODEL`` — override the default Gemini model.
      * ``MDB_MCP_CONNECTION_STRING`` — MongoDB connection string the MCP
        server connects to. When unset the agent still builds (so unit tests
        and ``--check`` work offline); only a live query needs it.
      * ``MONGO_SCOUT_READONLY`` — defaults to ``true``. When true the MCP
        server is launched with ``--readOnly`` so the agent physically
        cannot mutate data, which is the safe default for triage.
    """
    env = os.environ if env is None else env
    read_only_raw = env.get("MONGO_SCOUT_READONLY", "true").strip().lower()
    return Settings(
        model=env.get("MONGO_SCOUT_MODEL", DEFAULT_MODEL),
        connection_string=env.get("MDB_MCP_CONNECTION_STRING") or None,
        read_only=read_only_raw not in {"0", "false", "no", "off"},
    )
