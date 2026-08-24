from qdrant_client import QdrantClient
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode


from .models.agents_state import AgentState
from .product.product_qa import product_qa_agent

from .coordinator.coordinator_agent import coordinator_agent
from .shopping.shopping_cart import shopping_cart_agent
from .warehouse.warehouse_manager import warehouse_manager_agent
from .utils.product_qa_tools import get_formatted_items_context, get_formatted_reviews_context
from .utils.shopping_cart_tools import getting_shopping_cart, adding_to_shopping_cart, remove_from_cart , getting_user_shopping_cart
from .utils.warehouse_manager_tools import check_warehouse_availability, reserve_warehouse_items
from .utils.utils import get_tool_descriptions ,string_for_sse, process_graph_event, get_used_context
from langgraph.checkpoint.postgres import PostgresSaver


from helpers.config import get_settings
import json
settings= get_settings()
qdrant_clinet= QdrantClient(url=settings.QDRANT_URL)



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
    
def warehouse_manager_agent_tool_router(state) -> str:
    """Decide wheather to continue or end"""
    if state.warehouse_manager_agent.final_answer:
        return "end"
    elif state.warehouse_manager_agent.iterations >2 :
        return "end"

    elif len(state.warehouse_manager_agent.tool_calls) > 0 :
        return "tools"
    else:
        return "end" 

wf= StateGraph(AgentState)
product_qa_agent_tools= [get_formatted_items_context,get_formatted_reviews_context]
product_qa_tools_node= ToolNode(product_qa_agent_tools)
product_qa_tool_description= get_tool_descriptions(product_qa_agent_tools)



shopping_cart_agent_tools= [adding_to_shopping_cart,getting_shopping_cart,remove_from_cart]
shopping_cart_tools_node= ToolNode(shopping_cart_agent_tools)
shopping_cart_tool_description= get_tool_descriptions(shopping_cart_agent_tools)


warehouse_manager_agent_tools= [check_warehouse_availability,reserve_warehouse_items]
warehouse_manager_agent_tools_node= ToolNode(warehouse_manager_agent_tools)
warehouse_manager_agent_tool_description= get_tool_descriptions(warehouse_manager_agent_tools)


wf.add_node("coordinator_agent",coordinator_agent)

wf.add_node("product_qa_agent", product_qa_agent)
wf.add_node("product_qa_agent_tools", product_qa_tools_node)

wf.add_node("shopping_cart_agent", shopping_cart_agent)
wf.add_node("shopping_cart_agent_tools", shopping_cart_tools_node)

wf.add_node("warehouse_manager_agent", warehouse_manager_agent)
wf.add_node("warehouse_manager_agent_tools", warehouse_manager_agent_tools_node)


wf.add_edge(START,"coordinator_agent")

wf.add_conditional_edges(
    "coordinator_agent",
    coordinator_agent_edge,
    {
        "product_qa_agent":"product_qa_agent",
        "shopping_cart_agent":"shopping_cart_agent",
        "warehouse_manager_agent":"warehouse_manager_agent",

        "end": END,
    }
)


wf.add_conditional_edges(
    "product_qa_agent",
    product_qa_agent_edge,
    {
        "tools": "product_qa_agent_tools",
        "end": "coordinator_agent",
    }
)

wf.add_conditional_edges(
    "shopping_cart_agent",
    shopping_cart_agent_tool_router,
    {
        "tools": "shopping_cart_agent_tools",
        "end": "coordinator_agent"
    }
)


wf.add_conditional_edges(
    "warehouse_manager_agent",
    warehouse_manager_agent_tool_router,
    {
    "tools": "warehouse_manager_agent_tools",
    "end": "coordinator_agent"
    }
)




wf.add_edge("product_qa_agent_tools","product_qa_agent")
wf.add_edge("shopping_cart_agent_tools","shopping_cart_agent")
wf.add_edge("warehouse_manager_agent_tools","warehouse_manager_agent")


def run_agent_stream_wrapper(question:str, thread_id:str) :
    
    init_state={
            "messages": [{"role":"user","content":question}],
            "user_id":thread_id,
            "cart_id":thread_id,
            "product_qa_agent":{
                "iterations":0,
                "final_answer":False,
                "available_tools":product_qa_tool_description,
                "tool_calls":[]
            },
            "shopping_cart_agent":{
                            "iterations":0,
                            "final_answer":False,
                            "available_tools":shopping_cart_tool_description,
                            "tool_calls":[]
                        },
            "warehouse_manager_agent":{
                                        "iterations":0,
                                        "final_answer":False,
                                        "available_tools":warehouse_manager_agent_tool_description,
                                        "tool_calls":[]
                                    }

            }
    
    config= {
    "configurable":{
        "thread_id":thread_id
    }}
    with PostgresSaver.from_conn_string(settings.PRESISTANCE_STATE_URL) as checkpointer:
        graph= wf.compile(checkpointer)
        for chunk in  graph.stream(init_state,
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
            used_context= get_used_context(result["references"],qdrant_clinet)

        shopping_cart= getting_user_shopping_cart(thread_id,thread_id)
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
