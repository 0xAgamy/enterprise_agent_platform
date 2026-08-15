from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode


from .models.agents_state import AgentState
from .product.product_qa import product_qa_agent
from .utils.product_qa_tools import get_formatted_items_context
from .utils.utils import get_tool_descriptions

def product_qa_agent_tool_router(state) -> str:
    """Decide wheather to continue or end"""
    if state.final_answer:
        return "end"
    elif state.iterations >2 :
        return "end"

    elif len(state.tool_calls) > 0 :
        return "tools"
    else:
        return "end" 




wf= StateGraph(AgentState)
product_qa_agent_tools= [get_formatted_items_context]
product_qa_tools_node= ToolNode(product_qa_agent_tools)
product_qa_tool_description= get_tool_descriptions(product_qa_agent_tools)


wf.add_node("product_qa_agent", product_qa_agent)

wf.add_node("product_qa_agent_tools", product_qa_tools_node)


wf.add_edge(START,"product_qa_agent")



wf.add_conditional_edges(
    "product_qa_agent",
    product_qa_agent_tool_router,
    {
        "tools": "product_qa_agent_tools",
        "end": END,
    }
)

wf.add_edge("product_qa_agent_tools","product_qa_agent")





def run_agent(question:str)->dict:
    init_state={
            "messages": [{"role":"user","content":question}],
            "available_tools":product_qa_tool_description
            }

    graph= wf.compile()
    result= graph.invoke(init_state)

    return result

# png_bytes = graph.get_graph().draw_mermaid_png()

# with open("langgraph.png", "wb") as f:
#     f.write(png_bytes)