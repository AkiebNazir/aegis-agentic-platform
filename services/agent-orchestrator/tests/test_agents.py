from src.agents.swarm_handoffs import (
    route_to_initial_agent,
    determine_handoff,
    TRIAGE_AGENT,
    SRE_REMEDIATION_AGENT,
    ARCHITECTURE_AGENT,
)
from src.agents.state_recovery import SharedStateManager


def test_swarm_routing_and_handoff():
    agent = route_to_initial_agent("PaymentGateway has a P99 latency spike")
    assert agent.name == TRIAGE_AGENT.name

    next_agent = determine_handoff(agent)
    assert next_agent is not None
    assert next_agent.name == SRE_REMEDIATION_AGENT.name
    assert determine_handoff(next_agent) is None


def test_architecture_routing():
    agent = route_to_initial_agent("Explain the caching architecture")
    assert agent.name == ARCHITECTURE_AGENT.name


def test_state_checkpoint_recovery():
    mgr = SharedStateManager()
    mgr.save_checkpoint("req-123", {"step": "triage", "ok": True})
    loaded = mgr.load_checkpoint("req-123")
    assert loaded is not None
    assert loaded["step"] == "triage"