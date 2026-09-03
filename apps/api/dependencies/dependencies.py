from helpers.config import get_settings
import instructor
from litellm import completion
from agents.utils.mcp_utils import get_tool_descriptions_from_mcp_servers
from agents.graph import graph_builder
from typing import Optional

class AppDependencies:
    def __init__(self):
        self.settings= get_settings()
        self.llm_client= self._get_llm_client()
        self.mcp_tools=  None
        self.graph= None

    async def initialize(self):
        self.mcp_tools = await self._get_mcp_tools()
        self.graph = await graph_builder(
            self.llm_client,
            self.settings.OLLAMA_MODEL_NAME,
        )
        
        






    def _get_llm_client(self):
        return instructor.from_litellm(completion,mode=instructor.Mode.JSON)

    async def _get_mcp_tools(self):
        mcp_servers= [self.settings.MCP_URL]
        mcp_servers_tools =await get_tool_descriptions_from_mcp_servers(mcp_servers)
        return mcp_servers_tools


# Singleton instance
_app_deps: Optional[AppDependencies] = None

async def get_app_dependencies() -> AppDependencies:
    if _app_deps is None:
        raise RuntimeError("AppDependencies not initialized")
    return _app_deps

async def init_app_dependencies() -> AppDependencies:
    global _app_deps
    _app_deps = AppDependencies()
    await _app_deps.initialize()
    return _app_deps

async def shutdown_app_dependencies():
    global _app_deps
    if _app_deps:
        # _app_deps.cleanup()
        _app_deps = None