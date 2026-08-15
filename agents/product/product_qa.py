import instructor
from openai import OpenAI
from jinja2 import Template

from agents.models.schemas import ProdcutQAAgentResponse
from helpers.config import get_settings
from agents.utils.utils import to_llm_message, format_ai_message
settings= get_settings()
gen_client= OpenAI(
    api_key=settings.OLLAMA_API_KEY,
    base_url=settings.OLLAMA_BASE_URL
)



def product_qa_agent(state)->dict:
    prompt_template= """You're a shopping assistant that can answer questions about the products in stock

    You will be given a conversation history and a list of tools you can use to answer the latest query

    <Available tools>
    {{ available_tools | tojson}}
    </Available tools>

    When making a tool call, use this exact format
    
    {
        "name":"tool_name",
        "arguments": {
            "parameter1": "value1",
            "parameter2": "value2"
            }
    }

    CRITICAL: ALL parameters must go inside the "arguments" object not at the top of the tool calls 
    
    Examples:
    - get formatted item context 
    {
        "name":"get_formatted_item_context",
        "arguments": {
            "parameter1": "cool kids toys",
            "parameter2": "5"
            }
    }


    CRITICAL Rules:
    - if tool_calls has values, final_answer MUST be false.
    (You cannot call tools and exit the graph in the same response)
    - if the final_answer is true. tool_calls must be []
    (you must wait the tool results before exiting the graph)
    - After tool results are available and no more tool calls are needed, set final_answer=True.
    
    Instructions:
    - You need to answer the question based on the outputs from the tools using the available tools only.
    - Do not suggest the same tool call more than once.
    - If the question can be decomposed into multiple sub-questions, suggest all of them.
    - If multiple tool calls can be used at once to answer the questions, suggest all of them.
    - Do not explain your next steps in the answer, instead use tools to answer the question.
    - Never use word context and refer to it as the available products.
    - You should only answer questions about the products in stock. If the question is not about the products in stock, you should ask for clarification.

    * answer: The answer to the question based on your current knowledge and the tool results.
    * references: The list of the indexes from the chunks returned from all tool calls that were used to answer the question. If more than one chunk was used to compile the answer from a single tool call, be sure to return all of them.
    * Each reference should have an id and a short description of the item based on the retrieved context.
    * final_answer: True if you have all the information needed to provide a complete answer, False otherwise.

    - The answer to the question should contain detailed information about the product and should be returned with detailed specification.
    - The short description should have the name of the item.
    - If the user's request requires using a tool, set tool_calls with the appropriate function names and arguments.
        """.strip()

    template= Template(prompt_template)
    prompt= template.render(
        available_tools= state.available_tools
    )
    conversation= []
    for message in state.messages:
        conversation.append(to_llm_message(message))

    client= instructor.from_openai(gen_client,mode=instructor.Mode.JSON)
    response, _ = client.chat.completions.create_with_completion(
        model=settings.OLLAMA_MODEL_NAME,
        response_model=ProdcutQAAgentResponse,
        messages=[
            {"role":"system", "content":prompt},
            *conversation
        ]
    )
    ai_message= format_ai_message(response)

    return {
        "messages": [ai_message],
        "tool_calls": response.tool_calls,
        "iterations" : state.iterations + 1,
        "final_answer":response.final_answer,
        "references": response.references,
        "answer": response.answer
    }