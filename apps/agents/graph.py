from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.types import Command

from .models.agents_state import AgentState
from .product.product_qa import ProductQa

from .coordinator.coordinator_agent import Coordiantor
from .shopping.shopping_cart import ShoppingCart
from .warehouse.warehouse_manager import WarehouseManager
from .utils.product_qa_tools import ProductQATools
from .utils.shopping_cart_tools import ShoppingCartTools
from .utils.utils import string_for_sse, process_graph_event,  hitl_reservation
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver


from apps.helpers.config import get_settings
import json
from fastmcp import Client
from langchain.messages import ToolMessage
from apps.services.stores.VectorDB.QdrantDB import QdrantDBProvider
from apps.services.stores.PostgresDB.PostgreDB import PostgreService
settings= get_settings()

class EnterpriseAgentGraph:
    def __init__(self,llm_client, gen_model_name,qdrant_service:QdrantDBProvider,postgre_service:PostgreService,mcp_tools):
        self.llm_client= llm_client
        self.gen_model_name=gen_model_name
        self.qdrant_service= qdrant_service
        self.postgre_service=postgre_service
        self.mcp_tools= mcp_tools
        self.workflow= None
        
    async def initialize(self):
        self.workflow= await self._graph_builder()

    @staticmethod
    def coordinator_agent_edge(state):
        if state.coordinator_agent.iterations > 10:
            return "end"
        elif state.coordinator_agent.final_answer and len(state.coordinator_agent.plan)==0:
            return "end"
        elif state.coordinator_agent.next_agent== "product_qa_agent":
            return "product_qa_agent"
        elif state.coordinator_agent.next_agent== "shopping_cart_agent":
            return "shopping_cart_agent"
        elif state.coordinator_agent.next_agent== "warehouse_manager_agent":
            return "warehouse_manager_agent"
        else:
            return "end"

    @staticmethod
    def product_qa_agent_edge(state) -> str:
        """Decide wheather to continue or end"""
        if state.product_qa_agent.final_answer:
            return "end"
        elif state.product_qa_agent.iterations >2 :
            return "end"

        elif len(state.product_qa_agent.tool_calls) > 0 :
            return "tools"
        else:
            return "end" 
    @staticmethod
    def shopping_cart_agent_tool_router(state) -> str:
        """Decide wheather to continue or end"""
        if state.shopping_cart_agent.final_answer:
            return "end"
        elif state.shopping_cart_agent.iterations >2 :
            return "end"
        elif len(state.shopping_cart_agent.tool_calls) > 0 :
            return "tools"
        else:
            return "end" 
    @staticmethod
    def warehouse_manager_agent_tool_router(state) -> str:
        """Decide wheather to continue or end"""
        reservation= False
        for tool_call in state.warehouse_manager_agent.tool_calls:
            if tool_call.name=="reserve_warehouse_items":
                reservation= True
                break

        if state.warehouse_manager_agent.final_answer:
            return "end"
        elif state.warehouse_manager_agent.iterations >2 :
            return "end"

        elif len(state.warehouse_manager_agent.tool_calls) > 0 :
            if reservation:
                return "hitl_reservation"
            else:
                return "tools"
        else:
            return "end" 
    @staticmethod
    async def warehouse_manager_mcp_tool_call(state:AgentState):
        tool_messages=[]
        for i, tc in enumerate(state.warehouse_manager_agent.tool_calls):
            client= Client(tc.server)

            async with client:
                result= await client.call_tool(tc.name, tc.arguments)
                tool_message= ToolMessage(
                    content=result,
                    tool_call_id=f'call_{i}'
                )
                tool_messages.append(tool_message)
        return {
            "messages":tool_messages
        }


    async def _graph_builder(self):

        product_tools=ProductQATools(self.qdrant_service)

        product_qa_agent_tools=product_tools.tools()

        shppoing_cart_tools= ShoppingCartTools(self.postgre_service)
        shopping_cart_agent_tools=shppoing_cart_tools.tools()
        coordinator_agent= Coordiantor(self.gen_model_name,self.llm_client)
        product_qa_agent= ProductQa(self.gen_model_name,self.llm_client, product_tools.get_tools_descriptions())
        shopping_cart_agent= ShoppingCart(self.gen_model_name,self.llm_client,shppoing_cart_tools.get_tools_descriptions() )
        warehouse_manager_agent= WarehouseManager(self.gen_model_name,self.llm_client,self.mcp_tools)

        wf= StateGraph(AgentState)
        product_qa_tools_node= ToolNode(product_qa_agent_tools)
        shopping_cart_tools_node= ToolNode(shopping_cart_agent_tools)


        wf.add_node("warehouse_manager_mcp_tool_call", self.warehouse_manager_mcp_tool_call)


        wf.add_node("coordinator_agent",coordinator_agent)

        wf.add_node("product_qa_agent", product_qa_agent)
        wf.add_node("product_qa_agent_tools", product_qa_tools_node)

        wf.add_node("shopping_cart_agent", shopping_cart_agent)
        wf.add_node("shopping_cart_agent_tools", shopping_cart_tools_node)

        wf.add_node("warehouse_manager_agent", warehouse_manager_agent)
        wf.add_node("hitl_reservation",hitl_reservation)

        wf.add_edge(START,"coordinator_agent")

        wf.add_conditional_edges(
            "coordinator_agent",
            self.coordinator_agent_edge,
            {
                "product_qa_agent":"product_qa_agent",
                "shopping_cart_agent":"shopping_cart_agent",
                "warehouse_manager_agent":"warehouse_manager_agent",

                "end": END,
            }
        )


        wf.add_conditional_edges(
            "product_qa_agent",
            self.product_qa_agent_edge,
            {
                "tools": "product_qa_agent_tools",
                "end": "coordinator_agent",
            }
        )

        wf.add_conditional_edges(
            "shopping_cart_agent",
            self.shopping_cart_agent_tool_router,
            {
                "tools": "shopping_cart_agent_tools",
                "end": "coordinator_agent"
            }
        )


        wf.add_conditional_edges(
            "warehouse_manager_agent",
            self.warehouse_manager_agent_tool_router,
            {
            "tools": "warehouse_manager_mcp_tool_call",
            "hitl_reservation":"hitl_reservation",
            "end": "coordinator_agent"
            }
        )




        wf.add_edge("product_qa_agent_tools","product_qa_agent")
        wf.add_edge("shopping_cart_agent_tools","shopping_cart_agent")
        wf.add_edge("warehouse_manager_mcp_tool_call","warehouse_manager_agent")

        return wf


    async def run_agent_stream_wrapper(self,question:str, thread_id:str, mode:str) :
        if mode=="initialise":
            init_state={
                    "messages": [{"role":"user","content":question}],
                    "user_id":thread_id,
                    "cart_id":thread_id,
                    "product_qa_agent":{
                        "iterations":0,
                        "final_answer":False,
                        "tool_calls":[]
                    },
                    "shopping_cart_agent":{
                                    "iterations":0,
                                    "final_answer":False,
                                    "tool_calls":[]
                                },
                    "warehouse_manager_agent":{
                                                "iterations":0,
                                                "final_answer":False,
                                                
                                                "tool_calls":[]
                                            }

                    }
        if mode=="hitl":
            init_state=Command(
                resume={
                    "confirmed":question
                }
            )
            
        config= {
        "configurable":{
            "thread_id":thread_id
        }}
        async with AsyncPostgresSaver.from_conn_string(settings.PRESISTANCE_STATE_URL) as checkpointer:
            graph= self.workflow.compile(checkpointer)
            async for chunk in  graph.astream(init_state,
                                    config,
                                    stream_mode=["debug","values"]
                                    ):
                
                
                processes_chunk=process_graph_event(chunk)
                if processes_chunk:
                    yield string_for_sse(processes_chunk)
                
                if chunk[0]=="values":
                    result= chunk[1]
                    
            yield string_for_sse("[DONE]")
            used_context= []
            if len(result["references"]) > 0:
                used_context=self.qdrant_service.get_used_context(result["references"])
                # used_context= get_used_context(result["references"],qdrant_clinet)

            # shopping_cart= getting_user_shopping_cart(thread_id,thread_id)
            shopping_cart=self.postgre_service.get_user_shopping_cart_by_user_id(thread_id)
            shopping_cart_items= [{
                "price": float(item.get("price")) if item.get("price") else None,
                "quantity": item.get("quantity"),
                "currency": item.get("currency"),
                "product_image_url": item.get("product_image_url"),
                "total_price": float(item.get("total_price")) if item.get("total_price") else None,

            }
            for item in shopping_cart
            ]
        yield string_for_sse(json.dumps(
            {
                "type":"final_result",
                "data": {
                    "answer":   result.get("answer", ""),
                    "used_context": used_context,
                    "trace_id": result.get("trace_id",""),
                    "shopping_cart_items":shopping_cart_items
                }
            }
        ))
