from mongo_scout.config import DEFAULT_MODEL, load_settings


def test_defaults_when_env_empty():
    s = load_settings(env={})
    assert s.model == DEFAULT_MODEL
    assert s.connection_string is None
    assert s.has_live_db is False
    # read-only must default to True — the safe posture for an autonomous agent.
    assert s.read_only is True


def test_connection_string_picked_up():
    s = load_settings(env={"MDB_MCP_CONNECTION_STRING": "mongodb://localhost:27017"})
    assert s.connection_string == "mongodb://localhost:27017"
    assert s.has_live_db is True


def test_readonly_can_be_disabled():
    for val in ("false", "0", "no", "OFF"):
        s = load_settings(env={"MONGO_SCOUT_READONLY": val})
        assert s.read_only is False, val


def test_model_override():
    s = load_settings(env={"MONGO_SCOUT_MODEL": "gemini-2.5-pro"})
    assert s.model == "gemini-2.5-pro"
