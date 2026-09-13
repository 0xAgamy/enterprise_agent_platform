from fastapi import Request , APIRouter, Depends
from fastapi.responses import StreamingResponse
from ..models.schema import HitlRequest
from apps.api.dependencies.dependencies import AppDependencies,get_app_dependencies



hitl_router= APIRouter()

@hitl_router.post("/")
def hitl(request: Request,payload: HitlRequest, deps:AppDependencies= Depends(get_app_dependencies))->StreamingResponse:
    graph= deps.graph
    return StreamingResponse(
        graph.run_agent_stream_wrapper(
                                payload.approved,
                                payload.thread_id,
                                "hitl"),
        media_type="text/event-stream"
        )