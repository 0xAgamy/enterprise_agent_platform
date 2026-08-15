import inspect
from typing import Dict, Any
import ast

from langchain.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
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
    
    
    
