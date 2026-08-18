from fastapi import Request , APIRouter
from ..models.schema import AgentsReqesut, AgentsResponse, UsedContext
from agents.graph import run_agent_wrapper
agent_router = APIRouter()

@agent_router.post("/")
def agent(request: Request,payload: AgentsReqesut)->AgentsResponse:
    
    result= run_agent_wrapper(payload.query)
    return AgentsResponse(
        answer=result["answer"],
        references=[ UsedContext(**res) for res in result["used_context"] ]
    )
