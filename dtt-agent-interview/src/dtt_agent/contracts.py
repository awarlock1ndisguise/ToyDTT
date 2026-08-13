from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Input vocabulary (fixed by the assignment)
# ---------------------------------------------------------------------------

EVENT_TYPE_CHILD_RESPONSE = "child_response"

ANSWER_CORRECT = "correct"
ANSWER_INCORRECT = "incorrect"
ANSWER_NO_RESPONSE = "no_response"

#: The only answer values the simulator emits. They are already classified;
#: there is nothing to recognise, parse, match, or infer.
ALLOWED_ANSWERS = (ANSWER_CORRECT, ANSWER_INCORRECT, ANSWER_NO_RESPONSE)

#: Fields every child-answer event must carry.
REQUIRED_EVENT_FIELDS = ("event_id", "type", "session_id", "answer")

# ---------------------------------------------------------------------------
# Output vocabulary (fixed by the assignment)
# ---------------------------------------------------------------------------

STATUS_IDLE = "idle"
STATUS_RUNNING = "running"
STATUS_PAUSED = "paused"
STATUS_COMPLETE = "complete"
STATUS_TERMINATED = "terminated"

#: The only values `state.status` may take. Which of them your agent actually
#: uses, and when, is a protocol decision you make and document.
ALLOWED_STATUSES = (
    STATUS_IDLE,
    STATUS_RUNNING,
    STATUS_PAUSED,
    STATUS_COMPLETE,
    STATUS_TERMINATED,
)

#: Keys that must be present in every state snapshot.
REQUIRED_STATE_FIELDS = (
    "session_id",
    "status",
    "trial_number",
    "completed_trials",
    "protocol_state",
)

# ---------------------------------------------------------------------------
# Error codes
# ---------------------------------------------------------------------------
# These cover the software-contract rejections described in the README. You may
# add codes of your own; keep them SCREAMING_SNAKE_CASE strings.

ERROR_INVALID_EVENT = "INVALID_EVENT"
ERROR_SESSION_NOT_STARTED = "SESSION_NOT_STARTED"
ERROR_SESSION_MISMATCH = "SESSION_MISMATCH"
ERROR_INVALID_JSON = "INVALID_JSON"

#: Returned by the unimplemented starter agent so that the CLI and the public
#: contract tests run before you write any logic. Remove its uses as you go.
ERROR_NOT_IMPLEMENTED = "NOT_IMPLEMENTED"


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def make_action(
    action_type: str,
    text: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build one action entry.

    ``action_type`` is a non-empty string you define. ``text`` is optional
    free-form text (or ``None``). ``data`` is an optional JSON object carrying
    whatever structured detail that action type needs.
    """
    if not isinstance(action_type, str) or not action_type:
        raise ValueError("action_type must be a non-empty string")
    if text is not None and not isinstance(text, str):
        raise ValueError("text must be a string or None")
    if data is not None and not isinstance(data, dict):
        raise ValueError("data must be an object or None")
    return {"type": action_type, "text": text, "data": dict(data or {})}


def make_state(
    session_id: Optional[str],
    status: str,
    trial_number: Optional[int],
    completed_trials: int,
    protocol_state: Optional[str],
) -> Dict[str, Any]:
    """Build a state snapshot.

    ``protocol_state`` is a label you define. The scaffolding neither supplies
    nor interprets those labels.
    """
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"status must be one of {ALLOWED_STATUSES!r}")
    if trial_number is not None and not isinstance(trial_number, int):
        raise ValueError("trial_number must be an int or None")
    if not isinstance(completed_trials, int) or completed_trials < 0:
        raise ValueError("completed_trials must be a non-negative int")
    return {
        "session_id": session_id,
        "status": status,
        "trial_number": trial_number,
        "completed_trials": completed_trials,
        "protocol_state": protocol_state,
    }


def accepted_response(
    in_reply_to: Optional[str],
    actions: List[Dict[str, Any]],
    state: Dict[str, Any],
) -> Dict[str, Any]:
    """Build the envelope for an accepted event (``start_session`` uses ``None``)."""
    return {
        "in_reply_to": in_reply_to,
        "accepted": True,
        "actions": list(actions),
        "state": state,
    }


def rejected_response(
    in_reply_to: Optional[str],
    code: str,
    message: str,
    state: Dict[str, Any],
) -> Dict[str, Any]:
    """Build the envelope for a rejected event."""
    return {
        "in_reply_to": in_reply_to,
        "accepted": False,
        "actions": [],
        "error": {"code": code, "message": message},
        "state": state,
    }


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def validate_event_shape(event: Any) -> Optional[str]:
    """Check a child-answer event against the input schema.

    Returns ``None`` when the event is shaped correctly, otherwise a
    human-readable reason.

    This checks the *shape* only. Rules that depend on the agent's own state --
    answers arriving before a session starts, a session id that does not match
    the running session, an event id that has already been processed -- belong
    to the agent, because only the agent knows its state.
    """
    if not isinstance(event, dict):
        return "event must be a JSON object"

    missing = [field for field in REQUIRED_EVENT_FIELDS if field not in event]
    if missing:
        return f"event is missing required field(s): {', '.join(sorted(missing))}"

    for field in ("event_id", "type", "session_id"):
        value = event[field]
        if not isinstance(value, str) or not value.strip():
            return f"'{field}' must be a non-empty string"

    if event["type"] != EVENT_TYPE_CHILD_RESPONSE:
        return (
            f"'type' must be '{EVENT_TYPE_CHILD_RESPONSE}', got {event['type']!r}"
        )

    if event["answer"] not in ALLOWED_ANSWERS:
        return f"'answer' must be one of {list(ALLOWED_ANSWERS)}, got {event['answer']!r}"

    return None


def is_json_serializable(value: Any) -> bool:
    """Return ``True`` when ``value`` survives ``json.dumps``."""
    try:
        json.dumps(value)
    except (TypeError, ValueError):
        return False
    return True


def describe_state_violations(state: Any) -> List[str]:
    """Return the ways ``state`` breaks the state-snapshot contract."""
    problems: List[str] = []
    if not isinstance(state, dict):
        return ["state must be a JSON object"]

    for field in REQUIRED_STATE_FIELDS:
        if field not in state:
            problems.append(f"state is missing '{field}'")

    if "status" in state and state["status"] not in ALLOWED_STATUSES:
        problems.append(f"state.status must be one of {list(ALLOWED_STATUSES)}")

    session_id = state.get("session_id")
    if session_id is not None and not isinstance(session_id, str):
        problems.append("state.session_id must be a string or null")

    trial_number = state.get("trial_number")
    if trial_number is not None and (
        not isinstance(trial_number, int) or isinstance(trial_number, bool)
    ):
        problems.append("state.trial_number must be an integer or null")

    completed = state.get("completed_trials")
    if (
        not isinstance(completed, int)
        or isinstance(completed, bool)
        or completed < 0
    ):
        problems.append("state.completed_trials must be a non-negative integer")

    protocol_state = state.get("protocol_state")
    if protocol_state is not None and not isinstance(protocol_state, str):
        problems.append("state.protocol_state must be a string or null")

    return problems


def describe_response_violations(response: Any) -> List[str]:
    """Return the ways ``response`` breaks the output contract.

    An empty list means the envelope is well formed. This says nothing about
    whether the agent made good teaching decisions -- only that the response is
    shaped the way the runner and the graders expect.
    """
    problems: List[str] = []
    if not isinstance(response, dict):
        return ["response must be a JSON object"]

    if not is_json_serializable(response):
        problems.append("response must be JSON serializable")

    if "in_reply_to" not in response:
        problems.append("response is missing 'in_reply_to'")
    elif response["in_reply_to"] is not None and not isinstance(
        response["in_reply_to"], str
    ):
        problems.append("response.in_reply_to must be a string or null")

    accepted = response.get("accepted")
    if not isinstance(accepted, bool):
        problems.append("response.accepted must be a boolean")

    actions = response.get("actions")
    if not isinstance(actions, list):
        problems.append("response.actions must be a list")
    else:
        for index, action in enumerate(actions):
            problems.extend(
                f"actions[{index}]: {problem}"
                for problem in _describe_action_violations(action)
            )

    if accepted is False:
        error = response.get("error")
        if not isinstance(error, dict):
            problems.append("a rejected response must carry an 'error' object")
        else:
            for field in ("code", "message"):
                value = error.get(field)
                if not isinstance(value, str) or not value:
                    problems.append(f"error.{field} must be a non-empty string")
        if actions:
            problems.append("a rejected response must carry an empty 'actions' list")
    elif accepted is True and response.get("error") is not None:
        problems.append("an accepted response must not carry an 'error'")

    if "state" not in response:
        problems.append("response is missing 'state'")
    else:
        problems.extend(describe_state_violations(response["state"]))

    return problems


def _describe_action_violations(action: Any) -> List[str]:
    problems: List[str] = []
    if not isinstance(action, dict):
        return ["action must be a JSON object"]

    action_type = action.get("type")
    if not isinstance(action_type, str) or not action_type:
        problems.append("action.type must be a non-empty string")

    if "text" in action and action["text"] is not None:
        if not isinstance(action["text"], str):
            problems.append("action.text must be a string or null")

    if "data" in action and not isinstance(action["data"], dict):
        problems.append("action.data must be an object")

    return problems
