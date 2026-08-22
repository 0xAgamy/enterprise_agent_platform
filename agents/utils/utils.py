import inspect
from typing import Dict, Any
import ast
from helpers.config import get_settings
from typing import Any, Dict, Optional, Tuple

from langchain.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from qdrant_client.models import Filter, MatchValue, FieldCondition
settings= get_settings()
def parse_function_definition(function_def:str) -> Dict[str,Any]:
    """Parse a function definition string to extract metadata including type hits
    """
    results={
        "name": "",
        "description": "",

        "parameters": {
            "type": "object",
            "properties":{}
        },
        "required": [],
        "returns": {"type" : "string", "description": "" }
    }

    tree= ast.parse(function_def.strip())
    if not tree.body or not isinstance(tree.body[0], ast.FunctionDef):
        return results
    
    func= tree.body[0]
    results['name'] = func.name
    docstring= ast.get_docstring(func) or ""
    if docstring:
        docs_end= docstring.find("\n\n") if "\n\n" in docstring else docstring.find("\nArgs:")
        docs_end= docs_end if docs_end > 0 else docstring.find("\nParameters:")
        results["description"] = docstring[:docs_end].strip() if docs_end > 0 else docstring.strip()

        param_descs = parse_docstring_params(docstring)

        # Extract return description
        if "Returns:" in docstring:
            results["returns"]["description"] = (
                docstring.split("Returns:")[1]
                .strip()
                .split("\n")[0]
            )

    # Extract parameters with type hints
    args = func.args
    defaults = args.defaults
    num_args = len(args.args)
    num_defaults = len(defaults)

    for i, arg in enumerate(args.args):
        if arg.arg == "self":
            continue

        param_info = {
            "type": get_type_from_annotation(arg.annotation)
            if arg.annotation
            else "string",
            "description": param_descs.get(arg.arg, "")
        }

        # Check for default values
        default_idx = i - (num_args - num_defaults)
        if default_idx >= 0:
            param_info["default"] = ast.literal_eval(
                ast.unparse(defaults[default_idx])
            )
        else:
            results["required"].append(arg.arg)

        results["parameters"]["properties"][arg.arg] = param_info

    # Extract return type
    if func.returns:
        results["returns"]["type"] = get_type_from_annotation(func.returns)

    return results




def get_type_from_annotation(annotation) -> str:
    """Convert AST annotation to type string."""
    if not annotation:
        return "string"

    type_map = {
        'str': 'string',
        'int': 'integer',
        'float': 'number',
        'bool': 'boolean',
        'list': 'array',
        'dict': 'object',
        'List': 'array',
        'Dict': 'object',
    }

    if isinstance(annotation, ast.Name):
        return type_map.get(annotation.id, annotation.id)

    elif isinstance(annotation, ast.Subscript) and isinstance(annotation.value, ast.Name):
        base_type = annotation.value.id
        return type_map.get(base_type, base_type.lower())

    return "string"

def parse_docstring_params(docstring: str) -> Dict[str, str]:
    """Extract parameter descriptions from docstring (handles both Args: and Parameters: formats)."""
    params = {}
    lines = docstring.split('\n')
    in_params = False
    current_param = None

    for line in lines:
        stripped = line.strip()

        # Check for parameter section start
        if stripped in ['Args:', 'Arguments:', 'Parameters:', 'Params:']:
            in_params = True
            current_param = None
        elif stripped.startswith('Returns:') or stripped.startswith('Raises:'):
            in_params = False
        elif in_params:
            # Parse parameter line (handles "param: desc" and "- param: desc" formats)
            if ':' in stripped and (stripped[0].isalpha() or stripped.startswith('- ') or stripped.startswith('* ')):
                param_name = stripped.lstrip('- *').split(':')[0].strip()
                param_desc = ':'.join(stripped.lstrip('- *').split(':')[1:]).strip()
                params[param_name] = param_desc
                current_param = param_name
            elif current_param and stripped:
                # Continuation of previous parameter description
                params[current_param] += ' ' + stripped

    return params


def get_tool_descriptions(function_list):
    """Extract tool descriptions from the function list"""
    descriptions = []

    for function in function_list:
        function_string = inspect.getsource(function)
        result = parse_function_definition(function_string)

        if result:
            descriptions.append(result)

    return descriptions if descriptions else "Could not extract tool descriptions"





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
        else:
            return f"Unkown tool: {tool_call.name}"

    if _is_node_start(chunk):
        payload = chunk[1].get("payload", {})
        node_name = payload.get("name")
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
    else:
        return False





## helper function to get used context from references

def get_used_context(references, qdrant_clinet) ->list:
    used_context= []
    for item in references:
        
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
    return used_context
