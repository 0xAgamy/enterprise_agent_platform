from helpers.config import get_settings
import instructor
from litellm import completion
from agents.utils.mcp_utils import get_tool_descriptions_from_mcp_servers
from agents.graph import EnterpriseAgentGraph
from typing import Optional
from qdrant_client import QdrantClient

from services.reranking.reranking import Reranking
from services.embeddings.embedding import Embedding
from stores.VectorDB.QdrantDB import QdrantDBProvider
from stores.PostgresDB.PostgreDB import PostgreService
class AppDependencies:
    def __init__(self):
        self.settings= get_settings()
        self.llm_client= self._get_llm_client()
        self.mcp_tools=  None
        self.graph= None

    async def initialize(self):
        self.mcp_tools = await self._get_mcp_tools()
        self.graph = EnterpriseAgentGraph(
            llm_client=self.llm_client,
            gen_model_name=self.settings.OLLAMA_MODEL_NAME,
            qdrant_service=self._get_qdrant_service(),
            postgre_service=self._get_postgres_service(),
            mcp_tools=self.mcp_tools
        )
        await self.graph.initialize()
        
        


    def _get_reranking_service(self):
        return Reranking(
            self.settings.COHERE_API_KEY,
            self.settings.COHERE_RERANKING_MODEL
        )
    def _get_embedding_service(self):
        return Embedding(
            self.settings.OPENROUTER_API_KEY,
            self.settings.OPENROUTER_BASE_URL,
            self.settings.EMBEDDING_MODEL
        )

    def _get_qdrant_client(self):
        return QdrantClient(url=self.settings.QDRANT_URL)
    def _get_qdrant_service(self):
        return QdrantDBProvider(
            vdb_client=self._get_qdrant_client(),
            embedding_service=self._get_embedding_service(),
            reranking_service=self._get_reranking_service()
        )
    def _get_postgres_service(self):
        return PostgreService(self.settings.PRESISTANCE_STATE_URL)



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