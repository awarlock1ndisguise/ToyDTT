# PROTOCOL.md


## 1. Toy learning objective

Target Skill: Shape Recognition.
Lesson: Teaches the patient to recognize simple shapes.
Items: 3 (Circle, Square, Triangle).
Content: The content with the different shapes and prompts and reinforcement message lives in config.py. This way it's more organised and easily changeable.

> Clinical Disclaimer: This project is an educational computer simulation built solely to demonstrate state machine architecture. It does NOT constitute clinical guidance, medical advice or a substitute for professional ABA therapy.


## 2. Session and trial structure

A session holds the entire lesson run, where we go through all targeted trials of all shapes until all of them are finished. One trial contains the whole Stimulus-Learner Response-Consequence loop, it begins when the agent sends a status of PRESENT_SD and then it finishes when the protocol_state = "STARTING_SD" or "SESSION_COMPLETED".


## 3. Agent states

| `protocol_state` | Meaning | `status` reported alongside |
| --- | --- | --- |
| None | waiting for start_session() | 'idle' |
| STARTING_SD| beginning of a trial, presenting stimulus | 'running' |
| PROMPTING | Giving a prompt assistance after an incorrect or unanswered question | 'running' |
| SESSION_COMPLETED | All lesson targets have been finished | 'complete' |

## 4. Allowed transitions

| From | Answer / trigger | To | Actions emitted |
| --- | --- | --- | ---|
| IDLE | start_session() | STARTING_SD | PRESENT_SD |
| STARTING_SD | "correct" | STARTING_SD | DELIVER_REINFORCMENT |
| STARTING_SD | "correct" | STARTING_SD | SESSION_COMPLETED |
| STARTING_SD / PROMPTING | "incorrect" OR "no response (Attempts < 3) | PROMPTING | DELIVER_PROMPT|
| STARTING_SD / PROMPTING | "incorrect" OR "no response (Attempts >= 3, next target exits) | PROMPTING | DELIVER_PROMPT -> STARTING_SD |
| STARTING_SD / PROMPTING | "incorrect" OR "no response (Attempts >= 3, last target) | PROMPTING | SESSION_COMPLITED |

## 5. Action vocabulary

| Action `type` | Meaning | `text` | `data` keys |
| --- | --- | --- | --- |
| PRESENT_SD | asks the learner to perform the target skill| "Touch Circle" | "trial_number"=1, "target_id"= Circle "prompt_level"= independant |
| DELIVER_REINFORCMENT | Consequence after a correct answer | Correct! That's the Circle | "reward_type": "praise" |
| DELIVER_PROMPT | Consequence after a correct answer | Look closely! Point to the Circle | "prompt_level": "gestural_guide" |
| SESSION_COMPLETED | The lesson is complete | Session completed. Well Done! |
| "total_completed" = 3, "status"= completed |

## 6. Handling each answer

1. `correct` -  Emits DELIVER_REINFORCEMENT action then moves to the next target or otherwise emits SESSION_COMPLETED.
2. `incorrect` & `no_response` - It increments "_incorrect_attempts_on_target += 1" then if attempts < 3 emits DELIVER_PROMPT and the learner stays on the same target.
If attempts >= 3 emits DELIVER_PROMPT and advances to the next stage.

> 'incorrect' and 'no_response' are treated the same due to most of my research always referring to both responses with the same consequences.

## 7. Prompting strategy

A prompt is emitted immediately following an unsuccessful answer ("incorrect" or "no_response") as an extra helper action containing visual or verbal guidance. Prompting remains static and constant across attempts to keep the state machine simple and deterministic.

## 8. Error-correction strategy

Following an "incorrect" or "no_response" event, the agent emits a DELIVER_PROMPT action containing instructional guidance. The agent transitions to the PROMPTING state and re-presents the target item. The agent stops re-attempting an item when the learner provides a "correct" answer or when it reaches the 3-attempt cap on that specific target item.


## 9. Reinforcement strategy

Reinforcment is delivered immediately upon receiving a correct response. The Reinforcment reward_type: "praise" and it doesn't change. It remains static and continuous throughout the session; it does not change based on prompt level or session duration.


## 10. Trial completion rules

A trial ends when either the learner delivers a "correct" response or the learner exhausts the 3-attempt cap on a single target item. Every completed trial increments completed_trials by 1 and carries an implicit outcome of either passed (answered correctly) or max_attempts_reached.

## 11. Session completion, pause, and termination.

The condition for reaching 'complete' is for all trials to be completed (_current_target_index >= len(self._lesson)). 'paused' and 'terminated' are not implemented in this project.


## 12. Data recorded per trial

| Field Name | Type | Exposed in|
| trial_number| int| State & Action|
|completed_trials| int| State Snapshot|
|target_id| str| action data|
|prompt_level| str| action data|
|reward_type| str| Action Data|
|protocol_state| str| State Snapshot|


## 13. Repeated incorrect or absent answers

If a learner provides 3 unsuccessful answers ("incorrect" or "no_response") on the same target item:
1. self._incorrect_attempts_on_target reaches 3.
2. The agent emits a DELIVER_PROMPT action indicating target transition 
3. The agent increments _completed_trials and advances to the next lesson target in self._lesson.


## 14. Safety bound

A strict limit of maximum 3 attempts per target item is enforced in order to force  the trial to complete and advances to the next target item. If there isn't any trials the session is automatically completed.

## 15. Assumptions and exclusions

**Assumptions** — DTT does not prescribe exact software retry limits. 3 attempts were chosen to prevent learner frustration and state machine from looping forever.

**Exclusions** — 1. Excluded prompt level fading across attempts and  to reduce rule complexity in code.
2. Excluded Intertrial interval to keep event validation straightforward.

## 16. Source-to-rule traceability

| Protocol rule | Source support | Applicant assumption | Code location | Test location |
| --- | --- | --- | --- | --- |
| DELIVER_REINFORCEMENT post-correct answers | Yes: Frank-Crawford et al; Altun & Yucesoy-Ozkan | Gives the learner something to look forward to after each question | _evaluate_answer() Line 132 | test_process_correct_answer
| Deliver DELIVER_PROMPT when the answer is wrong or missing. | Altun & Yucesoy-Ozkan (2024) error correction. | To assist in getting a correct answer | _evaluate_answer() Line 153 | |test_process_incorrect_answer| Moves to the next target after 3 attempts | No | Yes: Prevents infinite loop | evaluate_answer() Line 141 |
