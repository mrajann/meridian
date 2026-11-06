import json
from types import SimpleNamespace

import anthropic
import pytest
from anthropic.types import Message, TextBlock, ToolUseBlock
from anthropic.types import Usage as SdkUsage

from meridian.agent import AnthropicClient
from meridian.agent.__main__ import main as cli_main
from meridian.agent.client import ModelResponse, Usage, _block_to_dict
from meridian.agent.scripted import ScriptedClient, reply, tool_use
from meridian.config import Settings
from meridian.indexing.__main__ import main as index_main


def sdk_message(**overrides) -> Message:
    fields = dict(
        id="msg_1",
        type="message",
        role="assistant",
        model="claude-test",
        stop_reason="tool_use",
        stop_sequence=None,
        content=[
            TextBlock(type="text", text="Checking.", citations=None),
            ToolUseBlock(type="tool_use", id="toolu_1", name="get_service", input={"name": "checkout-api"}),
        ],
        usage=SdkUsage(input_tokens=321, output_tokens=45, cache_read_input_tokens=7, cache_creation_input_tokens=3),
    )
    return Message(**{**fields, **overrides})


@pytest.fixture
def sdk(monkeypatch):
    """Replace anthropic.Anthropic with a stub that records create() calls."""
    calls = []
    outcome = {"message": sdk_message()}

    class StubAnthropic:
        def __init__(self, **kwargs):
            calls.append(("init", kwargs))
            self.messages = SimpleNamespace(create=self._create)

        def _create(self, **kwargs):
            calls.append(("create", kwargs))
            return outcome["message"]

    monkeypatch.setattr(anthropic, "Anthropic", StubAnthropic)
    return SimpleNamespace(calls=calls, outcome=outcome)


def test_the_adapter_flattens_sdk_blocks_into_plain_dicts_the_loop_can_echo_back(sdk):
    response = AnthropicClient("sk-test", "claude-test").create(
        system="s", messages=[{"role": "user", "content": "hi"}], tools=[], max_tokens=10
    )

    assert response.content == [
        {"type": "text", "text": "Checking."},
        {"type": "tool_use", "id": "toolu_1", "name": "get_service", "input": {"name": "checkout-api"}},
    ]
    assert response.stop_reason == "tool_use"
    assert response.usage == Usage(321, 45, 7, 3)
    json.dumps(response.content)  # plain data: no SDK objects leaked through


def test_the_adapter_sends_the_request_it_was_given(sdk):
    client = AnthropicClient("sk-test", "claude-test", timeout=30, max_retries=5)
    client.create(system="sys", messages=[{"role": "user", "content": "hi"}], tools=[{"name": "t"}], max_tokens=99)
    client.create(
        system="sys", messages=[], tools=[], max_tokens=1, tool_choice={"type": "tool", "name": "submit_report"}
    )

    init, first, second = sdk.calls[0], sdk.calls[1][1], sdk.calls[2][1]
    assert init[1] == {"api_key": "sk-test", "timeout": 30, "max_retries": 5}
    assert first == {
        "model": "claude-test", "system": "sys", "messages": [{"role": "user", "content": "hi"}],
        "tools": [{"name": "t"}], "max_tokens": 99,
    }
    assert "tool_choice" not in first  # not sent at all, rather than sent as null
    assert second["tool_choice"] == {"type": "tool", "name": "submit_report"}
    assert client.model == "claude-test"


def test_missing_cache_usage_counts_as_zero(sdk):
    sdk.outcome["message"] = sdk_message(usage=SdkUsage(input_tokens=5, output_tokens=6), content=[])

    response = AnthropicClient("sk-test", "m").create(system="", messages=[], tools=[], max_tokens=1)

    assert response.usage == Usage(5, 6, 0, 0) and response.content == []


def test_an_unknown_block_type_is_passed_through_without_null_fields():
    block = SimpleNamespace(type="thinking", model_dump=lambda exclude_none: {"type": "thinking", "thinking": "hm"})

    assert _block_to_dict(block) == {"type": "thinking", "thinking": "hm"}


def test_the_adapter_refuses_to_start_without_an_api_key():
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        AnthropicClient("", "claude-test")


# ------------------------------------------------------------------------ CLI


@pytest.fixture
def cli(tmp_path, monkeypatch):
    settings = Settings(embedding_backend="hashing", chroma_persist_dir=tmp_path / "chroma", anthropic_api_key="sk-test", _env_file=None)
    monkeypatch.setattr("meridian.indexing.__main__.settings", settings)
    monkeypatch.setattr("meridian.agent.__main__.settings", settings)
    index_main(["build"])
    return settings


def test_cli_lists_incidents(cli, capsys):
    capsys.readouterr()
    cli_main(["list"])

    ids = capsys.readouterr().out.split()
    assert len(ids) >= 100 and "alert-cascade-feature-flags-9" in ids


def test_cli_runs_an_incident_prints_the_report_and_writes_the_trace(cli, monkeypatch, capsys, tmp_path):
    report = {
        "severity": "SEV3", "severity_rationale": "Impact looks limited.", "affected_services": ["feature-flags"],
        "outcome": "insufficient_evidence", "evidence_gaps": ["Nothing retrieved describes this failure."],
        "recommended_action": "Ask the owning team to inspect the flag service configuration.",
    }
    scripted = ScriptedClient(reply(tool_use("get_service", {"name": "feature-flags"})), reply(tool_use("submit_report", report)))
    monkeypatch.setattr("meridian.agent.__main__.AnthropicClient", lambda key, model: scripted)
    capsys.readouterr()

    with pytest.raises(SystemExit) as exit_:
        cli_main(["run", "alert-cascade-feature-flags-9", "--trace-dir", str(tmp_path / "traces")])

    out = capsys.readouterr().out
    assert exit_.value.code == 0
    assert "completed" in out and "2 model calls" in out and "insufficient_evidence" in out
    [trace_file] = (tmp_path / "traces").glob("alert-cascade-feature-flags-9-*.json")
    assert json.loads(trace_file.read_text())["tool_calls"] == 2


def test_cli_exits_nonzero_when_the_run_fails(cli, monkeypatch, capsys, tmp_path):
    monkeypatch.setattr("meridian.agent.__main__.AnthropicClient", lambda key, model: ScriptedClient(reply(), reply()))

    with pytest.raises(SystemExit) as exit_:
        cli_main(["run", "alert-cascade-feature-flags-9", "--trace-dir", str(tmp_path)])

    assert exit_.value.code == 1 and "failed (no_report)" in capsys.readouterr().out


def test_cli_rejects_an_unknown_incident(cli):
    with pytest.raises(SystemExit, match="unknown incident"):
        cli_main(["run", "alert-does-not-exist"])
