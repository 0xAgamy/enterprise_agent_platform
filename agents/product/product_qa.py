import instructor
from openai import OpenAI
from jinja2 import Template

from agents.models.schemas import ProductQAAgentResponse
from helpers.config import get_settings
from helpers.prompt_management import prompt_template_config
from agents.utils.utils import to_llm_message, format_ai_message
from langsmith import traceable, get_current_run_tree
from litellm import completion

settings= get_settings()

client= instructor.from_litellm(completion,mode= instructor.Mode.JSON)




@traceable(
        name="Qna Agent",
        run_type="llm"
)
def product_qa_agent(state)->dict:
    template=prompt_template_config("agents/prompts/product_qa.yml","qa_agent")
    prompt= template.render(
        available_tools= state.product_qa_agent.available_tools
    )
    conversation = [
                to_llm_message(message)
                for message in state.messages
                ]

    response, raw_response = client.chat.completions.create_with_completion(
        model=settings.OLLAMA_MODEL_NAME,
        response_model=ProductQAAgentResponse,
        messages=[
            {"role":"system", "content":prompt},
            *conversation
        ]
    )

    current_run= get_current_run_tree()
    if current_run:
        current_run.metadata["usage_metadata"]={
            "input_tokens": raw_response.usage.prompt_tokens,
            "output_tokens": raw_response.usage.completion_tokens,
            "total_tokens": raw_response.usage.total_tokens,
            "cached_tokens": raw_response.usage.prompt_tokens_details.cached_tokens
        }
        
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
