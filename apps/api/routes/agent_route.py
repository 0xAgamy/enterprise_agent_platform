from fastapi import Request , APIRouter, Depends
from ..models.schema import AgentsRequest
from fastapi.responses import StreamingResponse
from apps.api.dependencies.dependencies import AppDependencies,get_app_dependencies
agent_router = APIRouter()

@agent_router.post("/")
async def agent(request: Request,payload: AgentsRequest, deps:AppDependencies= Depends(get_app_dependencies))->StreamingResponse:
    graph= deps.graph
    return StreamingResponse(
        graph.run_agent_stream_wrapper(
                                payload.query,
                                payload.thread_id,
                                "initialise"),
        media_type="text/event-stream"
    )
