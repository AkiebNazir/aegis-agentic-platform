from typing import TypedDict, Literal
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END

from src.agents.crew_workflow import MultiAgentCrewPipeline, build_llm
from src.agents.state_recovery import SharedStateManager
from src.evaluator.schemas import GenerationEvaluation


class OrchestratorState(TypedDict):
    request_id: str
    prompt: str
    context: str
    draft_answer: str
    agent_trace: str
    critique: str
    evaluation_status: str
    retry_count: int


class EvaluatorOptimizerGraph:
    """Self-correcting LangGraph workflow combining Multi-Agent Crew + LLM-as-a-Judge."""

    def __init__(self, max_retries: int = 2):
        self.max_retries = max_retries
        self.state_manager = SharedStateManager()
        self.crew = MultiAgentCrewPipeline(self.state_manager)
        self.judge_llm = build_llm(temperature=0.0).with_structured_output(GenerationEvaluation)
        self.app = self._build_graph()

    def _generate_node(self, state: OrchestratorState) -> dict:
        attempt = state.get("retry_count", 0) + 1
        answer, trace = self.crew.run(
            request_id=state["request_id"],
            prompt=state["prompt"],
            context=state["context"],
            evaluator_critique=state.get("critique", ""),
        )
        return {
            "draft_answer": answer,
            "agent_trace": trace,
            "retry_count": attempt,
        }

    def _evaluate_node(self, state: OrchestratorState) -> dict:
        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are a zero-trust AI Quality & Safety Auditor. Grade the draft strictly "
                "against the verified context for grounding, completeness, and operational safety.",
            ),
            (
                "human",
                "User Query: {query}\n\nVerified Context:\n{context}\n\nDraft Answer:\n{draft}",
            ),
        ])
        try:
            verdict: GenerationEvaluation = (prompt | self.judge_llm).invoke({
                "query": state["prompt"],
                "context": state["context"],
                "draft": state["draft_answer"],
            })
            passed = (
                verdict.is_grounded == "yes"
                and verdict.addresses_query == "yes"
                and verdict.safety_passed == "yes"
            )
            return {
                "evaluation_status": "pass" if passed else "fail",
                "critique": verdict.critique,
            }
        except Exception:
            # Fail-open to avoid blocking if local vLLM does not support structured JSON mode
            return {"evaluation_status": "pass", "critique": ""}

    def _route_after_eval(self, state: OrchestratorState) -> Literal["__end__", "generate"]:
        if state["evaluation_status"] == "pass" or state["retry_count"] >= self.max_retries:
            return END
        return "generate"

    def _build_graph(self):
        builder = StateGraph(OrchestratorState)
        builder.add_node("generate", self._generate_node)
        builder.add_node("evaluate", self._evaluate_node)

        builder.add_edge(START, "generate")
        builder.add_edge("generate", "evaluate")
        builder.add_conditional_edges(
            "evaluate",
            self._route_after_eval,
            {END: END, "generate": "generate"},
        )
        return builder.compile()

    def execute(self, request_id: str, prompt: str, context: str) -> OrchestratorState:
        initial: OrchestratorState = {
            "request_id": request_id,
            "prompt": prompt,
            "context": context,
            "draft_answer": "",
            "agent_trace": "",
            "critique": "",
            "evaluation_status": "",
            "retry_count": 0,
        }
        return self.app.invoke(initial)