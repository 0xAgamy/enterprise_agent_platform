from fastapi import FastAPI

from .routes.agent_route import agent_router
from .routes.feedback_route import feedback_router

app = FastAPI()
app.include_router(agent_router,prefix="/agent", tags=["agent"])
app.include_router(feedback_router,prefix="/submit_feedback", tags=["feedback"])

