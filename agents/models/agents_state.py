from pydantic import BaseModel, Field
from typing import Any, List ,Dict, Annotated
from operator import add



class RAGUsedContext(BaseModel):
    id: str= Field(description="The ID of the item used to answer the question")
    description:str = Field(description="Short description of the item used to answer the question")

class ToolCall(BaseModel):
    name:str
    arguments:dict[str, Any]


## Agent state

class AgentState(BaseModel):
    messages: Annotated[List[Any], add] = []
    answer:str=""
    iterations:int = 0
    tool_calls: List[ToolCall]=[]
    final_answer:bool= False
    references: Annotated[List[RAGUsedContext], add] = []
    available_tools: List[Dict[str,Any]] = []
