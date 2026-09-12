from typing import  Literal
from langgraph.graph import  END 
from langgraph.types import  Command, interrupt
from langsmith import traceable
from langchain.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
import json

def format_ai_message(response):
    if response.tool_calls:
        tool_calls=[]
        for i , tc in enumerate(response.tool_calls):
            tool_calls.append({
                    "id": f"call_{i}",
                    "name": tc.name,
                    "args": tc.arguments
            })
        
        return AIMessage(
            content=response.answer,
            tool_calls=tool_calls
        )
    else:
        return AIMessage(
            content=response.answer
        )


def to_llm_message(msg):
    if isinstance(msg, HumanMessage):
        return {
            "role": "user",
            "content": msg.content,

        }

    elif isinstance(msg, AIMessage):
        message= {}

        if msg.tool_calls:
            tool_calls=[]
            for i , tc in enumerate(msg.tool_calls):
                tool_calls.append({
                        "id": f"call_{i}",
                        "type":"function",
                        "function": {
                            "name": tc["name"],
                            "arguments": tc["args"]

                        }
                })
            message= {
                        "role": "assistant",
                        "content": msg.content,
                        "tool_calls": tool_calls
                    }
            
                
        else:
            message= {
                    "role": "assistant",
                    "content": msg.content,
                }
        
        return message
            

    elif isinstance(msg, SystemMessage):
        return {
            "role": "system",
            "content": msg.content,

        }
    
    elif isinstance(msg, ToolMessage):

        tool_message={
                "role": "tool",
                "content": msg.content,
                "tool_call_id": msg.tool_call_id,
            }
        return tool_message
    else:
        return msg
    
    
## helper functions for state streaming

def string_for_sse(message:str):
        return f"data: {message}\n\n"

def process_graph_event(chunk):
    def _is_interrupt(chunk):
        return len(chunk[1].get("payload", {}).get("interrupts",[])) > 0

    def _is_node_start(chunk):
        return chunk[1].get("type") == "task"

    def _is_node_end(chunk):

        return chunk[0]=="updates"

    def _tool_to_text(tool_call):
        if tool_call.name=="get_formatted_items_context":
            return f"looking for items: {tool_call.arguments.get('query','')}"
        elif tool_call.name=="get_formatted_reviews_context":
            return f"Fecting user reviews"
        elif tool_call.name=="adding_to_shopping_cart":
            return f"Add items to users shopping cart"
        elif tool_call.name=="getting_shopping_cart":
            return f"Getting user shopping cart items"
        elif tool_call.name=="remove_from_cart":
            return f"remove items from user shopping cart"
        elif tool_call.name=="check_warehouse_availability":
            return f"Check item availabality "
        elif tool_call.name=="reserve_warehouse_items":
            return f"Reservation "
        else:
            return f"Unkown tool: {tool_call.name}"

    if _is_node_start(chunk):
        payload = chunk[1].get("payload", {})
        node_name = payload.get("name")

        if node_name== "coordinator_agent":
            state = payload.get("input")
            if state.coordinator_agent.iterations == 0:
                return "Thinking" 
            
        if node_name== "product_qa_agent":
            state = payload.get("input")
            if state.product_qa_agent.iterations == 0:
                return "Anaylsing the Question" 
                
            if len(state.product_qa_agent.tool_calls) > 0:
                return "Reviewing the retrieved information..." 
        
        if node_name == "product_qa_agent_tools":
            state = payload.get("input")
            message=" ".join([_tool_to_text(tool_call) for tool_call in state.product_qa_agent.tool_calls])
            return message

        if node_name== "shopping_cart_agent":
            state = payload.get("input")
            if state.shopping_cart_agent.iterations == 0:
                return "Dealing with shopping cart" 
            if len(state.shopping_cart_agent.tool_calls) > 0:
                return "Analyise user shopping cart" 

        if node_name == "shopping_cart_agent_tools":
            state = payload.get("input")
            message=" ".join([_tool_to_text(tool_call) for tool_call in state.shopping_cart_agent.tool_calls])
            return message

        if node_name== "warehouse_manager_agent":
            state = payload.get("input")
            if state.warehouse_manager_agent.iterations == 0:
                return "Managing warehouse operations" 
            if len(state.warehouse_manager_agent.tool_calls) > 0:
                return "Managing inventory and fulfillment" 
        if node_name == "warehouse_manager_agent_tools":
            state = payload.get("input")
            message=" ".join([_tool_to_text(tool_call) for tool_call in state.warehouse_manager_agent.tool_calls])
            return message
    elif _is_interrupt(chunk):
        value= chunk[1].get("payload", {}).get("interrupts",[])[0].get("value")
        payload= {
            "type":"hitl_interrupt",
            "data":{
                "data":value
            }
        }
        return json.dumps(payload)
    else:
        return False


@traceable(
    name="HITL Reservation",
)
def hitl_reservation(state) -> Command[Literal["warehouse_manager_mcp_tool_call", "__end__"]]:
    for tool_call in state.warehouse_manager_agent.tool_calls:
        if tool_call.name == "reserve_warehouse_items":
                reservations_items=tool_call.arguments['reservations']
                break

    human_input=interrupt({
        "reservations_items":reservations_items
    })

    if human_input.get("confirmed"):
        return Command(
            update={},
            goto="warehouse_manager_mcp_tool_call"
        )
    else:

        last_message= state.messages[-1]
        santized= AIMessage(
        content=last_message.content,
            id= last_message.id
        )
        return Command(
            update={
                "messages":[santized],
                "answer":"You have rejected the Reservation of items."
                },
            goto=END
        )
    
