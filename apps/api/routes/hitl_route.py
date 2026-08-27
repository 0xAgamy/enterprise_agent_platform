from fastapi import Request , APIRouter
from fastapi.responses import StreamingResponse
from agents.graph import run_agent_stream_wrapper
from ..models.schema import HitlRequest



hitl_router= APIRouter()

@hitl_router.post("/")
def hitl(request: Request,payload: HitlRequest)->StreamingResponse:
    return StreamingResponse(
        run_agent_stream_wrapper(payload.approved,payload.thread_id,"hitl"),
        media_type="text/event-stream"
        )