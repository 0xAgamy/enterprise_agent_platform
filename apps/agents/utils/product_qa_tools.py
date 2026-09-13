
from langsmith import traceable
from langchain_core.tools import tool
from langchain_core.tools import StructuredTool
from apps.services.stores.VectorDB.QdrantDB import QdrantDBProvider

class ProductQATools:
    def __init__(self, qdrant_service:QdrantDBProvider):
        self.qdrant_service= qdrant_service

    def _process_items_context(self,context):
        format_context= ""
        for item in context["retrieved_context"]:
                format_context += (
                    f'- ID: {item["id"]}, '
                    f'rating: {item["rating"]}, '
                    f'description: {item["description"]}\n'
                )
            
        return format_context


    @traceable(
            name="Get formatted items context",
            run_type="tool"

    )
    def get_formatted_items_context(self,query:str, top_k:int=10) -> str:
        """Get the top k context, each representing an inventory for a given query.
        
        Args:
            query: the query to get top k context for, works best if it's more detailed
            top_k: the number of context chunks to retieve, works best for 10 or more.

        Returns:
            A string of the top k context chunks with IDs and average rating prepending each chunk, each repreasenting an inventory item for a given query.   
        """
        context= self.qdrant_service.reterive_data(
            query=query,
            collection_name= "Amazon_items",
            k=top_k
        )
        processed_context= self._process_items_context(context)
        return processed_context



    def _process_reviews_context(context):
        format_context= ""

        for id , chunk in zip(context["retrieved_context_ids"], context["retrieved_context"]):
            format_context+= f"- ID: {id}, reviews : {chunk}\n"
        return format_context

    @traceable(
            name="Get formatted reviews context",
            run_type="tool"

    )
    def get_formatted_reviews_context(self,query:str,item_list:list, top_k:int=15) -> str:
        """Get the top k reviews matching a query for a list of prefiltered items
        
        Args:
            query: the query to get top k reviews for
            item_list: The list of items IDs to prefilter for before running the query 
            top_k: the number of reviews  to retieve,this should be at least 10 if multiple items are prefiltered

        Returns:
            A string of the top k context chunks with IDs prepending each chunk, each representing a review for a given inventory item for a given query
        """
        context= self.qdrant_service.reterive_data(
            query=query,
            item_list=item_list,
            collection_name="Amazon_reviews",
            k=top_k
        )
        return self._process_reviews_context(context)



    def tools(self):
        return[
            StructuredTool.from_function(
                func= self.get_formatted_items_context
            ),
            StructuredTool.from_function(
                func= self.get_formatted_reviews_context
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


