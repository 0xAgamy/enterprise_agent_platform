from qdrant_client.models import  FieldCondition, Filter, Prefetch, FusionQuery, MatchAny, Document, MatchValue
from openai import OpenAI
from langsmith import traceable, get_current_run_tree
from qdrant_client import QdrantClient
from helpers.config import get_settings
from cohere import ClientV2

settings= get_settings()

embed_client= OpenAI(
    api_key=settings.OPENROUTER_API_KEY,
    base_url=settings.OPENROUTER_BASE_URL
)
cohere_client= ClientV2(
    api_key=settings.COHERE_API_KEY
)
qdrant_client= QdrantClient(url=settings.QDRANT_URL)

def _get_embedding(text, model=settings.EMBEDDING_MODEL):
    response= embed_client.embeddings.create(
        input= text,
        model=model,
        encoding_format="float"
    )
    return response.data[0].embedding

def _reranking(query:str, docs_to_reranking:list, k:int):
    reranked_results=[]

    try:
        reranking_response= cohere_client.rerank(
                model=settings.COHERE_RERANKING_MODEL,
                query=query,
                documents=docs_to_reranking,
                top_n=k
            )
        for result in reranking_response.results:
            if len(reranking_response.results) >= 10:
                if result.relevance_score > 0.8:
                    reranked_results.append(docs_to_reranking[result.index] )
            else:
                if result.relevance_score > 0.5:
                    reranked_results.append(docs_to_reranking[result.index] )
        return reranked_results
        
    except:
        return reranked_results



def _retrieve_items_data(query:str, k:int =5):

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


    to_rerank=retrieved_context
    reranked_retrieved_context= _reranking(query=query,
                                docs_to_reranking=to_rerank,
                                k=k)
    used_context=[]
    if len(reranked_retrieved_context) > 0:
        used_context=reranked_retrieved_context
    else:
        used_context=retrieved_context


    return {
        "retrieved_context_ids":retrieved_context_ids,
        "retrieved_context":used_context,
        "retrieved_context_rating":retrieved_context_rating,
        "similarity_score":similarity_score
    }


def _process_items_context(context):
    format_context= ""

    for id , chunk, rating in zip(context["retrieved_context_ids"], context["retrieved_context"], context["retrieved_context_rating"]):
        format_context+= f"- ID: {id}, rating: {rating}, description : {chunk}\n"
    return format_context



def get_formatted_items_context(query:str, top_k:int=10) -> str:
    """Get the top k context, each representing an inventory for a given query.
    
    Args:
        query: the query to get top k context for, works best if it's more detailed
        top_k: the number of context chunks to retieve, works best for 10 or more.

    Returns:
        A string of the top k context chunks with IDs and average rating prepending each chunk, each repreasenting an inventory item for a given query.   
    """
    context= _retrieve_items_data(query=query,k=top_k)
    
    processed_context= _process_items_context(context)
    return processed_context


### reviwes 


def _retrieve_reviwes_data(query:str,item_list, k:int =5):
    query_embedding= _get_embedding(query)
    results = qdrant_client.query_points(
    collection_name=settings.QDRANT_REVIEWS_COLLECTION_NAME,
    query=query_embedding,
    using="embedding",
    query_filter=Filter(
        must=[
            FieldCondition(
                key="parent_asin",
                match=MatchAny(any=item_list)
            )
        ]
    ),
    limit=k
    )

    retrieved_context_ids=[]
    retrieved_context=[]
    similarity_score=[]

    for result in results.points:
        retrieved_context_ids.append(result.payload["parent_asin"])
        retrieved_context.append(result.payload["text"])
        similarity_score.append(result.score)


    return {
        "retrieved_context_ids":retrieved_context_ids,
        "retrieved_context":retrieved_context,
        "similarity_score":similarity_score
    }


def _process_reviews_context(context):
    format_context= ""

    for id , chunk in zip(context["retrieved_context_ids"], context["retrieved_context"]):
        format_context+= f"- ID: {id}, reviews : {chunk}\n"
    return format_context


def get_formatted_reviews_context(query:str,item_list:list, top_k:int=15) -> str:
    """Get the top k reviews matching a query for a list of prefiltered items
    
    Args:
        query: the query to get top k reviews for
        item_list: The list of items IDs to prefilter for before running the query 
        top_k: the number of reviews  to retieve,this should be at least 10 if multiple items are prefiltered

    Returns:
        A string of the top k context chunks with IDs prepending each chunk, each representing a review for a given inventory item for a given query
    """

    return _process_reviews_context(_retrieve_reviwes_data(query,item_list,top_k))


