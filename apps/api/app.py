from fastapi import FastAPI, APIRouter, Request

from .routes.agent_route import agent_router

app = FastAPI()
app.include_router(agent_router,prefix="/agent", tags=["agent"])