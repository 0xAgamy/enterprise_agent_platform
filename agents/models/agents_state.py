from pydantic import BaseModel, Field
from typing import Any, List ,Dict, Annotated
from operator import add



class RAGUsedContext(BaseModel):
    id: str= Field(description="The ID of the item used to answer the question")
    description:str = Field(description="Short description of the item used to answer the question")

class ToolCall(BaseModel):
    name:str
    arguments:dict[str, Any]

## agent propoerties
class Delegation(BaseModel):
    agent:str
    task:str

class AgentProperties(BaseModel):
    iterations:int = 0
    available_tools: List[Dict[str,Any]] = []
    tool_calls: List[ToolCall]=[]
    final_answer:bool= False
class CoordinatorAgentProperties(BaseModel):
    iterations:int = 0
    final_answer:bool= False
    plan: List[Delegation] = []
    next_agent:str= ""
## Agent state

class AgentState(BaseModel):
    messages: Annotated[List[Any], add] = []
    user_intent:str= ""
    product_qa_agent: AgentProperties= Field(default_factory=AgentProperties)
    coordinator_agent: CoordinatorAgentProperties= Field(default_factory=CoordinatorAgentProperties)
    answer:str= ""
    references: Annotated[List[RAGUsedContext], add] = []
    trace_id:str=""

