from pydantic import BaseModel, Field
from typing import List, Union,Optional

class AgentsRequest(BaseModel):
    query:str= Field(...,description="The query/question Agentic pipeline")
    thread_id:str= Field(...,description="The thread ID")

class UsedContext(BaseModel):
    image_url:str= Field(...,description="The URL of the image of the item")
    price:Optional[float]= Field(...,description="The Price of the item")
    description: str= Field(...,description="a short description of the item")

class AgentsResponse(BaseModel):
    answer:str= Field(...,description="The Answer from Agentic pipeline")
    references:List[UsedContext]

### Feedback

class FeedbackRequest(BaseModel):
    feedback_score:Union[int, None]= Field(...,description="1 if the feedback is positive, 0 if the feedback is negative")
    trace_id:str= Field(...,description="The trace ID")
    thread_id:str= Field(...,description="The thread ID")

    feedback_text:str= Field(...,description="The Feedback text")
    feedback_score_type:str= Field(..., description="The type of feedback. Human or API")



class FeedbackResponse(BaseModel):
    status:str= Field(...,description="The Status of the feedback sumbession")
