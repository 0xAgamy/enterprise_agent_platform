from fastapi import Request , APIRouter
from ..models.schema import AgentsReqesut, AgentsResponse, UsedContext
from agents.graph import run_agent
agent_router = APIRouter()

@agent_router.post("/")
def agent(request: Request,payload: AgentsReqesut)->AgentsResponse:
    
    result= run_agent(payload.query)
    return AgentsResponse(
        answer=result["answer"],
        references=[ UsedContext(**res.model_dump()) for res in result["references"] ]
    )
