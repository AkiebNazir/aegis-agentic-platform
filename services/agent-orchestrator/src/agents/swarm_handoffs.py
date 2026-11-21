from dataclasses import dataclass
from typing import Callable, Dict, Tuple


@dataclass
class AgentProfile:
    name: str
    system_prompt: str


TRIAGE_AGENT = AgentProfile(
    name="IncidentTriageAgent",
    system_prompt=(
        "You are an Enterprise Incident Triage Agent. Analyze the GraphRAG service topology "
        "and runbooks to identify the root cause and affected downstream microservices."
    ),
)

SRE_REMEDIATION_AGENT = AgentProfile(
    name="SRERemediationAgent",
    system_prompt=(
        "You are a Principal SRE Remediation Agent. Using the Triage Agent's findings and "
        "verified runbooks, produce a safe, step-by-step remediation plan. Never invent commands."
    ),
)

ARCHITECTURE_AGENT = AgentProfile(
    name="ArchitectureAdvisorAgent",
    system_prompt=(
        "You are a Distributed Systems Architect. Explain system dependencies, caching tiers, "
        "and scaling bottlenecks strictly using the provided GraphRAG context."
    ),
)


def route_to_initial_agent(prompt: str) -> AgentProfile:
    """Deterministic router deciding which specialist agent handles the incoming prompt."""
    lower = prompt.lower()
    incident_keywords = ("latency", "spike", "error", "down", "timeout", "fix", "p99", "fail")
    if any(kw in lower for kw in incident_keywords):
        return TRIAGE_AGENT
    return ARCHITECTURE_AGENT


def determine_handoff(current_agent: AgentProfile) -> AgentProfile | None:
    """Defines explicit inter-agent handoff transitions."""
    if current_agent.name == TRIAGE_AGENT.name:
        return SRE_REMEDIATION_AGENT
    return None