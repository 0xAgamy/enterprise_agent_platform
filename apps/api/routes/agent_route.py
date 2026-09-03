from fastapi import Request , APIRouter, Depends
from ..models.schema import AgentsRequest
from fastapi.responses import StreamingResponse

from agents.graph import run_agent_stream_wrapper
from apps.api.dependencies.dependencies import AppDependencies,get_app_dependencies
agent_router = APIRouter()

@agent_router.post("/")
async def agent(request: Request,payload: AgentsRequest, deps:AppDependencies= Depends(get_app_dependencies))->StreamingResponse:
    workflow= deps.graph
    mcp_tools_description= deps.mcp_tools
    return StreamingResponse(
        run_agent_stream_wrapper(workflow,  
                                mcp_tools_description,
                                payload.query,
                                payload.thread_id,
                                "initialise"),
        media_type="text/event-stream"
    )
