import logging
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams , Distance, SparseVectorParams, Modifier,PayloadSchemaType, PointStruct, Document


class QdrantDBProvider:
    def __init__(self, vdb_client:str,vector_size:int=1024):
        self.client= None
        self.vdb_client=vdb_client
        self.vector_size=vector_size

    def connect(self):
        self.client= QdrantClient(url=self.vdb_client,timeout=60)


    def is_collection_exist(self,collection_name:str)->bool:
        self.client.collection_exists(collection_name)

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
            



