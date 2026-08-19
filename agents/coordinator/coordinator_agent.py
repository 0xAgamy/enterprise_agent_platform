import instructor
from openai import OpenAI
from jinja2 import Template
from langchain_core.messages import AIMessage

from agents.models.schemas import CoordinatorAgentResponse
from helpers.config import get_settings
from helpers.prompt_management import prompt_template_config
from agents.utils.utils import to_llm_message
from langsmith import traceable, get_current_run_tree

settings= get_settings()
gen_client= OpenAI(
    api_key=settings.OLLAMA_API_KEY,
    base_url=settings.OLLAMA_BASE_URL
)

@traceable(
        name="Coordinator Agent",
        run_type="llm"
)
def coordinator_agent(state) -> dict:
    
    
    template= prompt_template_config("agents/prompts/coordinator.yml","coordinator_agent")
    prompt= template.render()
    conversation=[]
    for message in state.messages:
        conversation.append(to_llm_message(message))
    
    client = instructor.from_openai(gen_client, mode= instructor.Mode.JSON)
    response, raw_response= client.chat.completions.create_with_completion(
        model= settings.OLLAMA_MODEL_NAME,
        messages=[
            {"role":"system", "content": prompt},
            *conversation
        ],

        response_model= CoordinatorAgentResponse
    )

    current_run= get_current_run_tree()
    if current_run:
        current_run.metadata["usage_metadata"]={
            "input_tokens": raw_response.usage.prompt_tokens,
            "output_tokens": raw_response.usage.completion_tokens,
            "total_tokens": raw_response.usage.total_tokens,
            "cached_tokens": raw_response.usage.prompt_tokens_details.cached_tokens
        }
        trace_id= str(getattr(current_run, "trace_id", current_run.id))

    if response.final_answer:
        ai_message=[AIMessage(
                    content=response.answer
                )]
    else:
        ai_message=[]

    return{
        "messages":ai_message,
        "answer": response.answer,
        "coordinator_agent":{
            "final_answer": response.final_answer,
            "next_agent": response.next_agent,
            "iterations": state.coordinator_agent.iterations +1,
            "plan": [p.model_dump()  for p in response.plan ]

        },
        "trace_id":trace_id
    }
