from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, IO, List, Optional, Sequence

from . import contracts
from .agent import DTTAgent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m dtt_agent",
        description=(
            "Run one simulated session: start a session, then feed one "
            "child-answer JSON object per input line."
        ),
    )
    parser.add_argument(
        "--session-id",
        default="demo",
        help="session id passed to start_session() (default: demo)",
    )
    parser.add_argument(
        "--input",
        metavar="PATH",
        type=argparse.FileType("r", encoding="utf-8"),
        default=None,
        help=(
            "read events from PATH instead of standard input; '-' also means "
            "standard input"
        ),
    )
    return parser


def run(
    agent: DTTAgent,
    session_id: str,
    stream: IO[str],
    out: IO[str],
) -> List[Dict[str, Any]]:
    """Drive ``agent`` over ``stream`` and return every emitted response."""
    emitted: List[Dict[str, Any]] = []

    def emit(response: Dict[str, Any]) -> None:
        emitted.append(response)
        out.write(json.dumps(response, sort_keys=True) + "\n")
        out.flush()

    emit(agent.start_session(session_id))

    for raw_line in stream:
        line = raw_line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            emit(_invalid_json(agent, f"line is not valid JSON: {exc}"))
            continue
        if not isinstance(event, dict):
            emit(_invalid_json(agent, "line is valid JSON but not an object"))
            continue
        emit(agent.process(event))

    return emitted


def _invalid_json(agent: DTTAgent, message: str) -> Dict[str, Any]:
    return contracts.rejected_response(
        in_reply_to=None,
        code=contracts.ERROR_INVALID_JSON,
        message=message,
        state=agent.get_state(),
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    stream = args.input or sys.stdin
    try:
        run(DTTAgent(), args.session_id, stream, sys.stdout)
    finally:
        if stream is not sys.stdin:
            stream.close()
    return 0


if __name__ == "__main__":  # pragma: no cover - `python -m dtt_agent.cli`
    raise SystemExit(main())
