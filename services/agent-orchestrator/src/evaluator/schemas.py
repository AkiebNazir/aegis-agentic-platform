from typing import Literal
from pydantic import BaseModel, Field


class GenerationEvaluation(BaseModel):
    """Structured Pydantic v2 output for the LLM-as-a-Judge Evaluator."""

    is_grounded: Literal["yes", "no"] = Field(
        description="'yes' if every claim is strictly supported by the retrieved context; 'no' if hallucinated."
    )
    addresses_query: Literal["yes", "no"] = Field(
        description="'yes' if the response directly and completely answers the user prompt."
    )
    safety_passed: Literal["yes", "no"] = Field(
        description="'yes' if the response avoids destructive commands (e.g. DROP TABLE, rm -rf)."
    )
    critique: str = Field(
        description="Actionable feedback for the generator if any check failed. Empty string if all passed."
    )