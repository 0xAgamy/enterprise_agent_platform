from fastapi import Request , APIRouter
from ..models.schema import AgentsRequest, AgentsResponse
from fastapi.responses import StreamingResponse

from agents.graph import run_agent_stream_wrapper
agent_router = APIRouter()

@agent_router.post("/")
def agent(request: Request,payload: AgentsRequest)->StreamingResponse:
    
    return StreamingResponse(
        run_agent_stream_wrapper(payload.query,payload.thread_id),
        media_type="text/event-stream"
    )
