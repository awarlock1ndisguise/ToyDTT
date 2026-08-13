import json
import subprocess
import sys
from pathlib import Path

import pytest

from dtt_agent import DTTAgent
from dtt_agent import contracts

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
SCENARIOS = REPO_ROOT / "scenarios"


@pytest.fixture()
def agent():
    return DTTAgent()


def valid_event(event_id="evt-001", session_id="demo", answer="correct"):
    return {
        "event_id": event_id,
        "type": contracts.EVENT_TYPE_CHILD_RESPONSE,
        "session_id": session_id,
        "answer": answer,
    }


def assert_valid_response(response):
    problems = contracts.describe_response_violations(response)
    assert not problems, "response violates the output contract: " + "; ".join(problems)


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------


def test_agent_exposes_the_required_methods(agent):
    for name in ("start_session", "process", "get_state", "reset"):
        assert callable(getattr(agent, name)), f"DTTAgent.{name} must be callable"


def test_idle_state_is_json_serializable_and_well_formed(agent):
    state = agent.get_state()
    assert contracts.is_json_serializable(state)
    assert not contracts.describe_state_violations(state)
    assert state["status"] == contracts.STATUS_IDLE
    assert state["completed_trials"] == 0


def test_start_session_returns_a_well_formed_envelope(agent):
    response = agent.start_session("demo")
    assert_valid_response(response)
    assert response["in_reply_to"] is None


def test_process_returns_a_well_formed_envelope(agent):
    agent.start_session("demo")
    assert_valid_response(agent.process(valid_event()))


# ---------------------------------------------------------------------------
# Rejections. Each one must be reported, not raised, and must leave state alone.
# ---------------------------------------------------------------------------


def test_answer_before_session_start_is_rejected_without_mutation(agent):
    before = agent.get_state()
    response = agent.process(valid_event())
    assert_valid_response(response)
    assert response["accepted"] is False
    assert agent.get_state() == before


@pytest.mark.parametrize(
    "event",
    [
        pytest.param(valid_event(answer="maybe"), id="unknown-answer"),
        pytest.param(valid_event(answer=""), id="empty-answer"),
        pytest.param(valid_event(answer=None), id="null-answer"),
        pytest.param(valid_event(answer="CORRECT"), id="wrong-case-answer"),
        pytest.param({"type": "child_response", "session_id": "demo", "answer": "correct"}, id="missing-event-id"),
        pytest.param(valid_event(event_id=""), id="empty-event-id"),
        pytest.param({"event_id": "evt-x", "type": "note", "session_id": "demo", "answer": "correct"}, id="wrong-type"),
        pytest.param({}, id="empty-object"),
    ],
)
def test_invalid_events_are_rejected_without_mutation(agent, event):
    agent.start_session("demo")
    before = agent.get_state()
    response = agent.process(event)
    assert_valid_response(response)
    assert response["accepted"] is False
    assert agent.get_state() == before


def test_session_id_mismatch_is_rejected_without_mutation(agent):
    agent.start_session("demo")
    before = agent.get_state()
    response = agent.process(valid_event(session_id="some-other-session"))
    assert_valid_response(response)
    assert response["accepted"] is False
    assert agent.get_state() == before


def test_rejected_responses_carry_a_code_and_a_message(agent):
    response = agent.process(valid_event(answer="maybe"))
    assert response["accepted"] is False
    assert response["actions"] == []
    assert response["error"]["code"]
    assert response["error"]["message"]


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------


def test_reset_returns_the_agent_to_a_clean_idle_state(agent):
    agent.start_session("demo")
    agent.process(valid_event())
    agent.reset()

    state = agent.get_state()
    assert state["status"] == contracts.STATUS_IDLE
    assert state["session_id"] is None
    assert state["completed_trials"] == 0
    assert state == DTTAgent().get_state()


def test_reset_clears_processed_event_history(agent):
    agent.start_session("demo")
    agent.process(valid_event())
    agent.reset()

    # The same event id must be usable again after a reset, so a fresh session
    # must not answer it out of the old history.
    agent.start_session("demo")
    response = agent.process(valid_event())
    assert_valid_response(response)
    assert response["in_reply_to"] == "evt-001"


# ---------------------------------------------------------------------------
# The provided runner
# ---------------------------------------------------------------------------


def run_cli(scenario_name):
    scenario = (SCENARIOS / scenario_name).read_text(encoding="utf-8")
    env_path = str(SRC_ROOT)
    completed = subprocess.run(
        [sys.executable, "-m", "dtt_agent", "--session-id", "demo"],
        input=scenario,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env={**_base_env(), "PYTHONPATH": env_path},
        timeout=60,
    )
    return completed, scenario


def _base_env():
    import os

    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    return env


@pytest.mark.parametrize(
    "scenario_name",
    [
        "all_correct.jsonl",
        "mixed_answers.jsonl",
        "repeated_incorrect.jsonl",
        "repeated_no_response.jsonl",
        "duplicate_event.jsonl",
        "invalid_values.jsonl",
    ],
)
def test_cli_emits_one_well_formed_line_per_input_line(scenario_name):
    completed, scenario = run_cli(scenario_name)
    assert completed.returncode == 0, completed.stderr

    input_lines = [line for line in scenario.splitlines() if line.strip()]
    output_lines = [line for line in completed.stdout.splitlines() if line.strip()]

    # One line for start_session(), then one per non-blank input line.
    assert len(output_lines) == len(input_lines) + 1

    for line in output_lines:
        assert_valid_response(json.loads(line))


def test_cli_input_flag_matches_stdin(tmp_path):
    """--input exists for shells without '<'; it must behave identically."""
    scenario = SCENARIOS / "mixed_answers.jsonl"
    env = {**_base_env(), "PYTHONPATH": str(SRC_ROOT)}

    from_flag = subprocess.run(
        [sys.executable, "-m", "dtt_agent", "--session-id", "demo", "--input", str(scenario)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env=env,
        timeout=60,
    )
    from_stdin = subprocess.run(
        [sys.executable, "-m", "dtt_agent", "--session-id", "demo"],
        input=scenario.read_text(encoding="utf-8"),
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env=env,
        timeout=60,
    )

    assert from_flag.returncode == 0, from_flag.stderr
    assert from_flag.stdout == from_stdin.stdout


def test_cli_survives_malformed_json(tmp_path):
    completed = subprocess.run(
        [sys.executable, "-m", "dtt_agent", "--session-id", "demo"],
        input='{"event_id": "evt-001", broken\nnot json at all\n[1, 2, 3]\n',
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env={**_base_env(), "PYTHONPATH": str(SRC_ROOT)},
        timeout=60,
    )
    assert completed.returncode == 0, completed.stderr

    lines = [json.loads(line) for line in completed.stdout.splitlines() if line.strip()]
    assert len(lines) == 4  # start_session + three unusable lines
    for response in lines[1:]:
        assert_valid_response(response)
        assert response["accepted"] is False
        assert response["error"]["code"] == contracts.ERROR_INVALID_JSON
