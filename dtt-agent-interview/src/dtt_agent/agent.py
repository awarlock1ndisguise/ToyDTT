from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import contracts
from .config import DEFAULT_LESSON


class DTTAgent:
   
    def __init__(self, lesson: List[Dict[str, str]] = DEFAULT_LESSON) -> None:

       
        self._lesson = lesson
        self._session_id: Optional[str] = None
        self._status: str = contracts.STATUS_IDLE
        self._trial_number: Optional[int] = None
        self._completed_trials: int = 0
        self._protocol_state: Optional[str] = None

        self._current_target_index: int = 0
        self._incorrect_attempts_on_target: int = 0  

       
        self._responses_by_event_id: Dict[str, Dict[str, Any]] = {}

    def get_state(self) -> dict:
        return contracts.make_state(
            session_id=self._session_id,
            status=self._status,
            trial_number=self._trial_number,
            completed_trials=self._completed_trials,
            protocol_state=self._protocol_state,
        )

    def reset(self) -> None:

        self._session_id = None
        self._status = contracts.STATUS_IDLE
        self._trial_number = None
        self._completed_trials = 0
        self._protocol_state = None

        self._current_target_index = 0
        self._incorrect_attempts_on_target = 0  

        self._responses_by_event_id.clear()

    def start_session(self, session_id: str) -> dict:
        self.reset()

        self._session_id = session_id
        self._status = contracts.STATUS_RUNNING
        self._trial_number = 1
        self._completed_trials = 0
        self._current_target_index = 0
        self._incorrect_attempts_on_target = 0
        self._protocol_state = "STARTING_SD"

        target = self._lesson[0]
        initial_action = contracts.make_action(
            action_type="PRESENT_SD",
            text=target["sd_text"],
            data={
                "trial_number": 1,
                "target_id": target["target_id"],
                "prompt_level": "independent",
            },
        )

        return contracts.accepted_response(
            in_reply_to=None,
            actions=[initial_action],
            state=self.get_state(),
        )

    def process(self, event: dict) -> dict:
       
        in_reply_to = event.get("event_id") if isinstance(event, dict) else None
        if not isinstance(in_reply_to, str):
            in_reply_to = None

        # 1. Validate event schema

        validation_error = contracts.validate_event_shape(event)
        if validation_error:
            return contracts.rejected_response(
                in_reply_to=in_reply_to,
                code=contracts.ERROR_INVALID_EVENT,
                message=validation_error,
                state=self.get_state(),
            )

        event_id = event["event_id"]
        event_session_id = event["session_id"]
        answer = event["answer"]

        # 2. Check if session has started

        if self._session_id is None or self._status == contracts.STATUS_IDLE:
            return contracts.rejected_response(
                in_reply_to=event_id,
                code=contracts.ERROR_SESSION_NOT_STARTED,
                message="No session has been started yet.",
                state=self.get_state(),
            )

        # 3. Check session ID mismatch

        if event_session_id != self._session_id:
            return contracts.rejected_response(
                in_reply_to=event_id,
                code=contracts.ERROR_SESSION_MISMATCH,
                message=f"Event session_id '{event_session_id}' does not match active session '{self._session_id}'.",
                state=self.get_state(),
            )

        # 4. Handle duplicate event_id idempotently

        if event_id in self._responses_by_event_id:
            return self._responses_by_event_id[event_id]

        # 5. Reject processing if session is not active

        if self._status != contracts.STATUS_RUNNING:
            return contracts.rejected_response(
                in_reply_to=event_id,
                code="SESSION_CLOSED",
                message=f"Cannot process answer in status '{self._status}'.",
                state=self.get_state(),
            )

        # 6. Evaluate answer & store response

        actions = self._evaluate_answer(answer)
        response = contracts.accepted_response(
            in_reply_to=event_id,
            actions=actions,
            state=self.get_state(),
        )

        self._responses_by_event_id[event_id] = response
        return response

    def _evaluate_answer(self, answer: str) -> List[Dict[str, Any]]:
        actions: List[Dict[str, Any]] = []
        target = self._lesson[self._current_target_index]

        if answer == contracts.ANSWER_CORRECT:
            self._incorrect_attempts_on_target = 0
            actions.append(
                contracts.make_action(
                    action_type="DELIVER_REINFORCEMENT",
                    text=f"Correct! That's the {target['label']}",
                    data={"reward_type": "praise"},
                )
            )
            self._advance_or_complete_trial(actions)
        else:
            self._incorrect_attempts_on_target += 1  

            if self._incorrect_attempts_on_target >= 3:

                
                self._incorrect_attempts_on_target = 0
                self._advance_or_complete_trial(actions)
            else:
                self._protocol_state = "PROMPTING"
                actions.append(
                    contracts.make_action(
                        action_type="DELIVER_PROMPT",
                        text=target["prompt_text"],
                        data={
                            "target_id": target["target_id"],
                            "prompt_level": "gestural_guide",
                        },
                    )
                )

        return actions

    def _advance_or_complete_trial(self, actions: List[Dict[str, Any]]) -> None:
        self._completed_trials += 1
        self._current_target_index += 1

        if self._current_target_index < len(self._lesson):
            self._trial_number = self._current_target_index + 1
            self._protocol_state = "STARTING_SD"
            next_target = self._lesson[self._current_target_index]
            actions.append(
                contracts.make_action(
                    action_type="PRESENT_SD",
                    text=next_target["sd_text"],
                    data={
                        "trial_number": self._trial_number,
                        "target_id": next_target["target_id"],
                        "prompt_level": "independent",
                    },
                )
            )
        else:
            self._status = contracts.STATUS_COMPLETE
            self._trial_number = None
            self._protocol_state = "SESSION_COMPLETE"
            actions.append(
                contracts.make_action(
                    action_type="SESSION_COMPLETED",
                    text="Session completed. Well done!",
                    data={
                        "total_completed": self._completed_trials,
                        "status": contracts.STATUS_COMPLETE,
                    },
                )
            )