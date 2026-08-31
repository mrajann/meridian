from meridian.config import Settings


def test_defaults_when_no_env_file():
    s = Settings(_env_file=None)
    assert s.environment == "development"
    assert s.log_level == "INFO"
    assert s.anthropic_model == "claude-sonnet-4-5"
    assert s.anthropic_api_key == ""


def test_environment_variables_override_defaults(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    s = Settings(_env_file=None)

    assert s.environment == "production"
    assert s.log_level == "DEBUG"


def test_env_file_is_loaded(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("ANTHROPIC_API_KEY=test-key-123\n")

    s = Settings(_env_file=str(env_file))

    assert s.anthropic_api_key == "test-key-123"
