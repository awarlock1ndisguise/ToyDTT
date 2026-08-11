import pytest
from dtt_agent import DTTAgent
from dtt_agent import contracts

@pytest.fixture
def agent():
    a = DTTAgent()
    a.start_session("demo")
    return a

def make_event(event_id: str, answer: str):
    return {
        "event_id": event_id,
        "type": contracts.EVENT_TYPE_CHILD_RESPONSE,
        "session_id": "demo",
        "answer": answer,
    }

def test_process_correct_answer(agent):
    event = make_event("evt-001", contracts.ANSWER_CORRECT)
    response = agent.process(event)

    assert response["in_reply_to"] == "evt-001"
    assert response["accepted"] is True

    reinforcement_= response["actions"][0]
    assert reinforcement_["type"] == "DELIVER_REINFORCEMENT"
    assert reinforcement_["data"]["reward_type"] == "praise"

    assert agent.get_state()["completed_trials"] == 1
    assert agent.get_state()["trial_number"] == 2

def test_process_incorrect_answer(agent):
    event = make_event("evt-002", contracts.ANSWER_INCORRECT)
    response = agent.process(event)

    assert response["in_reply_to"] == "evt-002"
    assert response["accepted"] is True

    prompt_action = response["actions"][0]
    assert prompt_action["type"] == "DELIVER_PROMPT"
    assert prompt_action["data"]["prompt_level"] == "gestural_guide"

    assert agent.get_state()["completed_trials"] == 0
    assert agent.get_state()["trial_number"] == 1

def test_no_response_triggers_prompt(agent):
    event = make_event("evt-001", contracts.ANSWER_NO_RESPONSE)
    response = agent.process(event)

    assert response["accepted"] is True
    assert len(response["actions"]) == 1
    assert response["actions"][0]["type"] == "DELIVER_PROMPT"
    
   
    assert agent.get_state()["completed_trials"] == 0
    assert agent.get_state()["trial_number"] == 1

def test_multiple_incorrect_then_correct(agent):
   
    event1 = make_event("evt-001", contracts.ANSWER_INCORRECT)
    response1 = agent.process(event1)
    assert response1["accepted"] is True
    assert response1["actions"][0]["type"] == "DELIVER_PROMPT"
    assert agent.get_state()["completed_trials"] == 0
    assert agent.get_state()["trial_number"] == 1

   
    event2 = make_event("evt-002", contracts.ANSWER_INCORRECT)
    response2 = agent.process(event2)
    assert response2["accepted"] is True
    assert response2["actions"][0]["type"] == "DELIVER_PROMPT"
    assert agent.get_state()["completed_trials"] == 0
    assert agent.get_state()["trial_number"] == 1

   
    event3 = make_event("evt-003", contracts.ANSWER_CORRECT)
    response3 = agent.process(event3)
    assert response3["accepted"] is True
    assert response3["actions"][0]["type"] == "DELIVER_REINFORCEMENT"
    assert agent.get_state()["completed_trials"] == 1
    assert agent.get_state()["trial_number"] == 2

def test_full_session_completion(agent):
    
    agent.process(make_event("evt-001", contracts.ANSWER_CORRECT))
    agent.process(make_event("evt-002", contracts.ANSWER_CORRECT))
    response3 = agent.process(make_event("evt-003", contracts.ANSWER_CORRECT))

    assert response3["accepted"] is True
    assert response3["actions"][-1]["type"] == "SESSION_COMPLETED"
    assert agent.get_state()["status"] == contracts.STATUS_COMPLETE

    response4 = agent.process(make_event("evt-004", contracts.ANSWER_CORRECT))
    assert response4["accepted"] is False
    assert response4["error"]["code"] == "SESSION_CLOSED"
   
