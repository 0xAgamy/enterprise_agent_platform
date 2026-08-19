from pydantic import BaseModel, Field
from typing import List, Dict,Optional

class AgentsRequest(BaseModel):
    query:str= Field(...,description="The query/question Agentic pipeline")


class UsedContext(BaseModel):
    image_url:str= Field(...,description="The URL of the image of the item")
    price:Optional[float]= Field(...,description="The Price of the item")
    description: str= Field(...,description="a short description of the item")

class AgentsResponse(BaseModel):
    answer:str= Field(...,description="The Answer from Agentic pipeline")
    references:List[UsedContext]

