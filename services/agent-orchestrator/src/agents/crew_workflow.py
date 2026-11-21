import os
from typing import Tuple
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from src.agents.swarm_handoffs import route_to_initial_agent, determine_handoff
from src.agents.state_recovery import SharedStateManager, execute_with_recovery


def build_llm(temperature: float = 0.1) -> ChatOpenAI:
    return ChatOpenAI(
        model=os.getenv("VLLM_MODEL", "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"),
        api_key=os.getenv("VLLM_API_KEY", "local-vllm-airgapped"),
        base_url=os.getenv("VLLM_BASE_URL", "http://localhost:8001/v1"),
        temperature=temperature,
    )


class MultiAgentCrewPipeline:
    """Executes deterministic multi-agent handoffs with shared state checkpointing."""

    def __init__(self, state_manager: SharedStateManager):
        self.state_manager = state_manager
        self.llm = build_llm(temperature=0.1)

    def run(
        self,
        request_id: str,
        prompt: str,
        context: str,
        evaluator_critique: str = "",
    ) -> Tuple[str, str]:
        agent = route_to_initial_agent(prompt)
        trace = [agent.name]
        handoff_notes = ""

        while agent is not None:
            feedback_block = (
                f"\n\nCRITICAL EVALUATOR FEEDBACK TO FIX:\n{evaluator_critique}"
                if evaluator_critique
                else ""
            )
            prompt_tmpl = ChatPromptTemplate.from_messages([
                ("system", "{system_prompt}{feedback_block}"),
                (
                    "human",
                    "User Query: {query}\n\nVerified Context:\n{context}\n\n"
                    "Prior Agent Handoff Notes:\n{handoff_notes}",
                ),
            ])

            def _invoke() -> str:
                res = (prompt_tmpl | self.llm).invoke({
                    "system_prompt": agent.system_prompt,
                    "feedback_block": feedback_block,
                    "query": prompt,
                    "context": context,
                    "handoff_notes": handoff_notes or "None (initial agent)",
                })
                return str(res.content)

            output = execute_with_recovery(
                _invoke,
                fallback_msg=f"[Fallback {agent.name}]: Verified context:\n{context}",
            )

            handoff_notes = output
            self.state_manager.save_checkpoint(
                request_id,
                {"trace": trace, "last_agent": agent.name, "output": output},
            )

            next_agent = determine_handoff(agent)
            if next_agent:
                trace.append(next_agent.name)
            agent = next_agent

        return handoff_notes, " -> ".join(trace)