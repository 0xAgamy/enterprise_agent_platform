import instructor
from openai import OpenAI
from jinja2 import Template

from agents.models.schemas import ProdcutQAAgentResponse
from helpers.config import get_settings
from helpers.prompt_management import prompt_template_config
from agents.utils.utils import to_llm_message, format_ai_message
settings= get_settings()
gen_client= OpenAI(
    api_key=settings.OLLAMA_API_KEY,
    base_url=settings.OLLAMA_BASE_URL
)

def product_qa_agent(state)->dict:
    template=prompt_template_config("agents/prompts/product_qa.yml","qa_agent")
    prompt= template.render(
        available_tools= state.product_qa_agent.available_tools
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
        "product_qa_agent":{
            "tool_calls": [tool_call.model_dump() for tool_call in response.tool_calls],
            "final_answer": response.final_answer,
            "iterations" : state.product_qa_agent.iterations + 1,
            "available_tools": state.product_qa_agent.available_tools
        },
        "answer": response.answer,
        "references" : response.references
    }
