from qdrant_client.models import  FieldCondition, Filter, Prefetch, FusionQuery, MatchAny, Document, MatchValue
from openai import OpenAI
from langsmith import traceable, get_current_run_tree
from qdrant_client import QdrantClient
from helpers.config import get_settings

settings= get_settings()

embed_client= OpenAI(
    api_key=settings.OPENROUTER_API_KEY,
    base_url=settings.OPENROUTER_BASE_URL
)


def _get_embedding(text, model=settings.EMBEDDING_MODEL):
    response= embed_client.embeddings.create(
        input= text,
        model=model,
        encoding_format="float"
    )
    

    return response.data[0].embedding

def _retieve_items_data(query:str, qdrant_client:QdrantClient, k:int =5):
    qdrant_client= QdrantClient(url=settings.QDRANT_URL)
    query_embedding= _get_embedding(query)
    results= qdrant_client.query_points(
        collection_name=settings.QDRANT_ITEMS_COLLECTION_NAME,
        prefetch=[
                Prefetch(
                    query=query_embedding,
                    limit=20,
                    using="embedding"
                ),

                Prefetch(
                    query=Document(
                        text=query,
                        model="qdrant/bm25"
                    ),
                    limit=20,
                    using="bm25"
                ),

        ],
        query= FusionQuery(fusion='rrf'),
        limit=k
    )  
    retrieved_context_ids=[]
    retrieved_context=[]
    similarity_score=[]
    retrieved_context_rating=[]

    for result in results.points:
        retrieved_context_ids.append(result.payload["parent_asin"])
        retrieved_context.append(result.payload["description"])
        retrieved_context_rating.append(result.payload["average_rating"])
        similarity_score.append(result.score)





    return {
        "retrieved_context_ids":retrieved_context_ids,
        "retrieved_context":retrieved_context,
        "retrieved_context_rating":retrieved_context_rating,
        "similarity_score":similarity_score
    }


def _process_items_context(context):
    format_context= ""

    for id , chunk, rating in zip(context["retrieved_context_ids"], context["retrieved_context"], context["retrieved_context_rating"]):
        format_context+= f"- ID: {id}, rating: {rating}, description : {chunk}\n"
    return format_context



def get_formatted_items_context(query:str, top_k:int=5) -> str:
    """Get the top k context, each representing an inventory for a given query.
    
    Args:
        query: the query to get top k context for 
        top_k: the number of context chunks to retieve, works best for 5 or more.

    Returns:
        A string of the top k context chunks with IDs and average rating prepending each chunk, each repreasenting an inventory item for a given query.   
    """

    context= _retieve_items_data(query,top_k)
    
    processed_context= _process_items_context(context)
    return processed_context

