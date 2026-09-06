import logging
from qdrant_client import QdrantClient
from qdrant_client.models import (VectorParams , Distance, SparseVectorParams,
                                Modifier,PayloadSchemaType,MatchAny , Document,
                                FieldCondition,Filter,Prefetch ,FusionQuery, MatchValue)

from services.embeddings.embedding import Embedding
from services.reranking.reranking import Reranking
class QdrantDBProvider:
    def __init__(self, vdb_client:QdrantClient, embedding_service:Embedding, reranking_service:Reranking, vector_size:int=1024 ):
        self.client= vdb_client
        self.vector_size=vector_size
        self.embedding_service= embedding_service
        self.reranking_service= reranking_service



    def is_collection_exist(self,collection_name:str)->bool:
        return self.client.collection_exists(collection_name)

    def create_collections(self, collection_name:str):

        self.client.create_collection(
            collection_name=collection_name,
            vectors_config={
                "embedding": VectorParams(size=self.vector_size,distance= Distance.COSINE)
            },
        sparse_vectors_config={
            "bm25":SparseVectorParams(modifier=Modifier.IDF)
        }
        )

    def create_indexing(self, collection_name:str, field_name:str):
        
        self.client.create_payload_index(
            collection_name=collection_name,
            field_name=field_name,
            field_schema=PayloadSchemaType.KEYWORD
        )


    def batch_insert(self,collection_name:str,pointstruct, batch_size:int=100):

        
        for i in range(0 , len(pointstruct), batch_size):
            batch= pointstruct[i:i+batch_size]
            self.client.upsert(
                    collection_name=collection_name,
                    points= batch,
                    wait=True
            )

    def reterive_data(self, query, collection_name, k , list_items:list[str]|None = None):
        query_embeddings= self.embedding_service.get_embeddings(query)
        if collection_name== "Amazon_reviews":
            if not list_items:
                raise ValueError("item_list is required when retrieving reviews")
            results = self.client.query_points(
                    collection_name=collection_name,
                    query=query_embeddings,
                    using="embedding",
                    query_filter=Filter(
                        must=[
                            FieldCondition(
                                key="parent_asin",
                                match=MatchAny(any=list_items)
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
        elif collection_name=="Amazon_items":
            results = self.client.query_points(
            collection_name=collection_name,
            prefetch=[
                Prefetch(
                    query=query_embeddings,
                    limit=20,
                    using="embedding",
                ),
                Prefetch(
                    query=Document(
                        text=query,
                        model="qdrant/bm25",
                    ),
                    limit=20,
                    using="bm25",
                ),
            ],
            query=FusionQuery(fusion="rrf"),
            limit=k,
        )

            retrieved_context = []

            for result in results.points:
                retrieved_context.append(
                    {
                        "id": result.payload["parent_asin"],
                        "description": result.payload["description"],
                        "rating": result.payload["average_rating"],
                        "similarity_score": result.score,
                    }
                )
            try:
                response=self.reranking_service.get_ranking(query,retrieved_context,"description",k)
                threshold = 0.8 if len(retrieved_context) >= 10 else 0.5
                reranked_results=[]
                for result in response.results:
                    if result.relevance_score > threshold:
                        item = retrieved_context[result.index].copy()
                        item["rerank_score"] = result.relevance_score
                        reranked_results.append(item)
                
            except Exception as e :
                print(e)
            used_context= reranked_results or retrieved_context
        return {
            "retrieved_context": used_context,
        }


    def get_used_context(self, references) ->list:
        used_context= []
        for item in references:
            
            points= self.client.query_points(
                collection_name= "Amazon_items",
        
                limit=1,
                with_payload=True,
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="parent_asin",
                            match=MatchValue(value=item.id)
                        )
                    ]
                )

            )
            if not points.points: continue
            payload= points.points[0].payload

            image_url= payload.get("image","")
            price= payload.get("price","")

            if image_url:
                used_context.append(
                    {
                        "image_url":image_url,
                        "price":price,
                        "description":item.description
                    }
                )
        return used_context




            


        

            



