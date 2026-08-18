import instructor
from openai import OpenAI
from jinja2 import Template
from langchain_core.messages import AIMessage

from agents.models.schemas import CoordinatorAgentResponse
from helpers.config import get_settings
from helpers.prompt_management import prompt_template_config
from agents.utils.utils import to_llm_message
settings= get_settings()
gen_client= OpenAI(
    api_key=settings.OLLAMA_API_KEY,
    base_url=settings.OLLAMA_BASE_URL
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
        # reasoning_effort="none",
        response_model= CoordinatorAgentResponse
    )
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

        }
    }
