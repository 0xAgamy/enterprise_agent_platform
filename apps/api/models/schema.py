from pydantic import BaseModel, Field
from typing import List, Dict
class AgentsReqesut(BaseModel):
    query:str= Field(...,description="The query/question Agentic pipeline")


class UsedContext(BaseModel):
    id: str= Field(description="The ID of the item used to answer the question")
    description:str = Field(description="Short description of the item used to answer the question")

class AgentsResponse(BaseModel):
    answer:str= Field(...,description="The Answer from Agentic pipeline")
    references:List[UsedContext]

