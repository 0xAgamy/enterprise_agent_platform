from fastapi import FastAPI

from .routes.agent_route import agent_router
from .routes.feedback_route import feedback_router
from .routes.hitl_route import hitl_router

app = FastAPI()
app.include_router(agent_router,prefix="/agent", tags=["agent"])
app.include_router(feedback_router,prefix="/submit_feedback", tags=["feedback"])
app.include_router(hitl_router,prefix="/hitl",tags=["Human_In_The_Loop"])

