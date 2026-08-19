from pydantic import BaseModel, Field
from typing import List
from .agents_state import ToolCall, RAGUsedContext, Delegation




class CoordinatorAgentResponse(BaseModel):
    next_agent:str
    plan: List[Delegation]
    final_answer:bool
    answer:str


class ProductQAAgentResponse(BaseModel):
    answer:str= Field(description="Full Answer to the question")
    references: List[RAGUsedContext] = Field(description="List of items used to answer the quesiton",default_factory=list)
    final_answer: bool = False
    tool_calls: List[ToolCall] = Field(default_factory=list)

