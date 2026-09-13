from typing import Annotated
from langgraph.prebuilt import InjectedState
from apps.agents.models.agents_state import AgentState
from langsmith import traceable
from apps.services.stores.PostgresDB.PostgreDB import PostgreService
from langchain_core.tools import StructuredTool

class ShoppingCartTools:
    def __init__(self, postgre_service:PostgreService):
        self.postgre_service= postgre_service
        

    @traceable(
        name="Add items to user shopping cart",
        run_type="tool"
    )
    def adding_to_shopping_cart(self,items: list[dict], state: Annotated[AgentState, InjectedState]):
        """Adding a list of provided itmes to the user's shopping cart

        Args:
            items: a list of items to add to the shopping cart. Each item is a dictonary with the following keys: product_id, quantity.
        Returns:
            A list of the items adding to shopping cart.
        """
        user_id= state.user_id
        cart_id= state.cart_id
        result= self.postgre_service.add_to_shopping_cart(items,user_id, cart_id)
        return result

    @traceable(
        name="Get user items from shopping cart",
        run_type="tool"
    )
    def getting_shopping_cart(self,state: Annotated[AgentState, InjectedState]):
        """Retrieve all items in a user's shopping cart

        Args:

        Return:
            List of dictionaries containing cart items
        """
        user_id= state.user_id
        cart_id= state.cart_id
        user_shopping_cart= self.postgre_service.get_user_shopping_cart(user_id,cart_id)
        return f"User Shopping Cart Items are: \n{user_shopping_cart}"


    @traceable(
        name="Remove user item in shopping cart",
        run_type="tool"
)
    def remove_from_cart(self,product_id:str,  state: Annotated[AgentState, InjectedState])->str:
        """Remove an item complately from the user's shopping cart

        Args:
            product_id: product id to remove the product from user shopping cart
        Return:
            True if item was removed, False if the item wasn't found

        """

        user_id= state.user_id
        cart_id= state.cart_id
        result=self.postgre_service.remove_from_shopping_cart(product_id,user_id,cart_id)
        if result:
            return f"Item with {product_id} id was removed successfully "
        else:
            return f"Item with {product_id} was not removed, Error happens "
        

    def tools(self):
            return[
                StructuredTool.from_function(
                    func= self.getting_shopping_cart
                ),
                StructuredTool.from_function(
                    func= self.adding_to_shopping_cart
                ),
            ]
    
    def get_tools_descriptions(self):
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "args": tool.args_schema.model_json_schema(),
            }
            for tool in self.tools()]