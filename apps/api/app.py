from fastapi import FastAPI
from contextlib import asynccontextmanager
from .routes.agent_route import agent_router
from .routes.feedback_route import feedback_router
from .routes.hitl_route import hitl_router

from apps.api.dependencies.dependencies import init_app_dependencies, get_app_dependencies, shutdown_app_dependencies

async def startup_span(app:FastAPI):
    depends= await init_app_dependencies()
    app.state.depends=depends

@asynccontextmanager
async def lifespan(app:FastAPI):
    await startup_span(app)
    yield
    await shutdown_app_dependencies()

app = FastAPI(lifespan=lifespan)
app.include_router(agent_router,prefix="/agent", tags=["agent"])
app.include_router(feedback_router,prefix="/submit_feedback", tags=["feedback"])
app.include_router(hitl_router,prefix="/hitl",tags=["Human_In_The_Loop"])

