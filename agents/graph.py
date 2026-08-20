from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode


from .models.agents_state import AgentState
from .product.product_qa import product_qa_agent
from .coordinator.coordinator_agent import coordinator_agent
from .utils.product_qa_tools import get_formatted_items_context, get_formatted_reviews_context
from .utils.utils import get_tool_descriptions
from langgraph.checkpoint.postgres import PostgresSaver


from helpers.config import get_settings
settings= get_settings()



def coordinator_agent_edge(state):
    if state.coordinator_agent.iterations > 10:
        return "end"
    elif state.coordinator_agent.final_answer and len(state.coordinator_agent.plan)==0:
        return "end"
    elif state.coordinator_agent.next_agent== "product_qa_agent":
        return "product_qa_agent"
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




wf= StateGraph(AgentState)
product_qa_agent_tools= [get_formatted_items_context,get_formatted_reviews_context]
product_qa_tools_node= ToolNode(product_qa_agent_tools)
product_qa_tool_description= get_tool_descriptions(product_qa_agent_tools)


wf.add_node("product_qa_agent", product_qa_agent)

wf.add_node("product_qa_agent_tools", product_qa_tools_node)

\
wf.add_node("coordinator_agent",coordinator_agent)


wf.add_edge(START,"coordinator_agent")

wf.add_conditional_edges(
    "coordinator_agent",
    coordinator_agent_edge,
    {
        "product_qa_agent":"product_qa_agent",
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

wf.add_edge("product_qa_agent_tools","product_qa_agent")





def run_agent(question:str, thread_id:str)->dict:
    init_state={
            "messages": [{"role":"user","content":question}],
            "product_qa_agent":{
                "iterations":0,
                "final_answer":False,
                "available_tools":product_qa_tool_description,
                "tool_calls":[]
            }}
    
    config= {
    "configurable":{
        "thread_id":thread_id
    }}

    with PostgresSaver.from_conn_string(settings.PRESISTANCE_STATE_URL) as checkpointer:

    
        graph= wf.compile(checkpointer)
        result= graph.invoke(init_state,config)

    # png_bytes = graph.get_graph().draw_mermaid_png()

    # with open("langgraph.png", "wb") as f:
    #     f.write(png_bytes)

    return result


def run_agent_wrapper(question:str, thread_id:str) :
    qdrant_clinet= QdrantClient(url=settings.QDRANT_URL)

    result= run_agent(question=question, thread_id=thread_id)
    used_context= []
    if len(result["references"]) > 0:
        for item in result.get("references", []):
            
            points= qdrant_clinet.query_points(
                collection_name= settings.QDRANT_ITEMS_COLLECTION_NAME,
        
                limit=1,
                with_payload=True,
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="parent_asin",
                            match=MatchValue(value=item.id)
                        )
                    ]
                )

            )
            if not points.points: continue
            payload= points.points[0].payload

            image_url= payload.get("image","")
            price= payload.get("price","")

            if image_url:
                used_context.append(
                    {
                        "image_url":image_url,
                        "price":price,
                        "description":item.description
                    }
                )
    return{
        "answer":   result.get("answer", ""),
        "used_context": used_context,
    }
