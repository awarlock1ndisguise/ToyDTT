# ToyDTT Project.
---
## What is this project about?

This project is a Discrete Trial Training (DTT) simulation developed in Python. Using starter code provided by the Intelligent-Robotics-Lab, including DTTAgent class signatures (src/dtt_agent/agent.py), event schemas and response wrappers (src/dtt_agent/contracts.py), a CLI runner, and six public contract tests (tests/test_public_contract.py). I researched behavioral intervention principles and implemented a custom DTT state machine agent.

## The DTT Agent.

The agent runs a mock lesson focused on **shape recognition**. A standard session consists of **3 items** (`Circle`, `Square`, and `Triangle`). All target metadata, prompt texts, and Discriminative Stimuli ($S^D$) are defined sequentially inside `config.py`.


## Architechture

A single session contains 3 sequential trials (one per shape target):

1. **Stimulus Presentation ($S^D$):** The agent presents the instruction prompt to the learner based on the current target in `config.py`.
2. **Evaluation:** The agent processes the learner's response (`"correct"`, `"incorrect"`, or `"no_response"`).
   * **Correct Answer:** The agent delivers verbal praise (`DELIVER_REINFORCEMENT`) and advances to the next trial.
   * **Incorrect / No Response:** The agent delivers a helpful prompt (`DELIVER_PROMPT`).
3. **Completion & Safety Bounds:**
   * If a learner answers incorrectly **3 times on the same item**, the agent delivers guidance and forces advancement to the next target.
   * Once all 3 shape targets are completed, the agent updates its state to `SESSION_COMPLETED`.

---

## How to run everything 

> Install Python **3.11 or newer**.

-Run the following code, line by line .

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS or Linux
source .venv/bin/activate

python -m pip install -e ".[dev]"

```
- Verify that the installation and CLI runner are working properly:

```
python -m pytest
python -m dtt_agent --session-id demo --input scenarios/mixed_answers.jsonl
```
## Assumptions 

- Using 3 attempts per trial: None of the sources I cite in RESEARCH_TEMPLATE.md ever states aything about using 3 chances for the learner to get it correct. This being becasue the sources have reaserched their papers around the concept of implying DTT between human interaction instead of a software program. Where in one, during session with human therapies they cannot let tehir learner say 'incorrect' a finite of times while a computer can. So in order for ther eto be a boundary, we put 3 attemps for the loop to stop.

## TradeOffs

- Trading clinical realism for software reliability. By using fixed, predictable rules instead of dynamic prompt fading and varied praise, I made a state machine that is 100% predictable and easy to test, though less adaptive than real human therapy.
- Traded guaranteed lesson completion for strict skill mastery. The 3-attempt limit ensures every session finishes without getting stuck, but it means a learner might move on to the next item before fully mastering the current one.

## Disclaimer 
 This project is an educational computer simulation built solely to demonstrate state machine architecture. It does NOT constitute clinical guidance, medical advice or a substitute for professional ABA therapy.