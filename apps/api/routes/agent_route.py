from fastapi import Request , APIRouter
from ..models.schema import AgentsRequest
from fastapi.responses import StreamingResponse

from agents.graph import run_agent_stream_wrapper
agent_router = APIRouter()

@agent_router.post("/")
async def agent(request: Request,payload: AgentsRequest)->StreamingResponse:
    
    return StreamingResponse(
        run_agent_stream_wrapper(payload.query,payload.thread_id, "initialise"),
        media_type="text/event-stream"
    )
