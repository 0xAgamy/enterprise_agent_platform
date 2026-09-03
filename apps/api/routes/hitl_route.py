from fastapi import Request , APIRouter, Depends
from fastapi.responses import StreamingResponse
from agents.graph import run_agent_stream_wrapper
from ..models.schema import HitlRequest
from apps.api.dependencies.dependencies import AppDependencies,get_app_dependencies



hitl_router= APIRouter()

@hitl_router.post("/")
def hitl(request: Request,payload: HitlRequest, deps:AppDependencies= Depends(get_app_dependencies))->StreamingResponse:
    workflow= deps.graph
    mcp_tools_description= deps.mcp_tools
    return StreamingResponse(
        run_agent_stream_wrapper(workflow,
                                mcp_tools_description,
                                payload.approved,
                                payload.thread_id,"hitl"),
        media_type="text/event-stream"
        )