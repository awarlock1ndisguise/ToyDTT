# AI_USE.md

## 1. Tools used

| Tool | Version / model, if known | What you used it for |
| Gemini | 3.6 | Understanding code structure, drafting test case and troubleshooting state machine bugs|


## 2. Tasks delegated

Asked AI to break down the code provided for this project, into plain English.  
The important prompts or tasks you handed to an AI tool. 
Asked the AI to write test cases in tests/test_my_protocol.py to check that state updates and answer checks worked correctly.
Asked the AI to code the checks for valid messages, duplicate message IDs, active session status and handing off answers to be evaluated.

## 3. Generated code and text you kept

1. Test_my_protocol.py: Kept generated test cases for checking correct answers, wrong answers, missing responses, multiple retry attempts and session termination.
2. 3 attempts target retry cap logic.
3. process() in agent.py: Kept the structure for event validation, duplicate event checking, and active status validation.

## 4. Verification

Ran pytest & tests/test_my_protocol.py to ensure all unit tests passed. Ran scenario files via the command line using python -m dtt_agent --session-id demo < scenarios/<file_name>.jsonl to verify CLI outputs and catch error codes. 

## 5. One suggestion you accepted, and one you rejected

- **Accepted:** Accepted the suggestion to cache processed responses in self._responses_by_event_id. This ensures that if a duplicate event_id is sent, the agent immediately returns the saved response without double-counting if the exact same message gets sent twice.
- **Rejected or changed:** Rejected to implement dynamic least-to-most prompt fading and multi-tier praise levels across the session. Instead, kept prompt levels static (gestural_guide) and praise uniform (DELIVER_REINFORCEMENT) to prevent overcomplicating the state machine logic.

## 6. Statement

> I am responsible for every source, statement, design choice, and line of code
> in this submission. I can explain and modify any part of it.

Name: Ana Begaj
Date: 08/11/2026
