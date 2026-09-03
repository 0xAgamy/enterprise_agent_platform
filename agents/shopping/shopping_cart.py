from agents.models.schemas import ShoppingCartAgentResponse
from helpers.prompt_management import prompt_template_config
from agents.utils.utils import to_llm_message, format_ai_message
from langsmith import traceable, get_current_run_tree

class ShoppingCart:
    def __init__(self, model_name, llm_client):
        self.model_name= model_name
        self.llm_client = llm_client
        self.template= prompt_template_config("agents/prompts/shopping.yml","shopping_agent")


    @traceable(
            name="Shopping Cart Agent",
            run_type="llm"
    )
    def __call__(self,state) -> dict:
        
        prompt=self.template.render(
            available_tools= state.shopping_cart_agent.available_tools,

        )
        conversation = [
                        to_llm_message(message)
                        for message in state.messages
                        ]


        response, raw_response= self.llm_client.chat.completions.create_with_completion(
            model= self.model_name,
            messages=[
                {"role":"system", "content": prompt},
                *conversation
            ],
            response_model=ShoppingCartAgentResponse    
            
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
            "shopping_cart_agent":{
                "tool_calls": [tool_call.model_dump() for tool_call in response.tool_calls],
                "final_answer": response.final_answer,
                "iterations" : state.shopping_cart_agent.iterations + 1,
                "available_tools": state.shopping_cart_agent.available_tools
            },
            "answer": response.answer,
        }