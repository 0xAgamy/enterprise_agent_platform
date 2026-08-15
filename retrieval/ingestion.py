from helpers.config import get_settings
from stores.VectorDB.QdrantDB import QdrantDBProvider
from retrieval.embedding import get_embedding_batch, get_items_data, get_reviews_data
from qdrant_client.models import PointStruct, Document
from openai import OpenAI


settings= get_settings()
embed_client= OpenAI(
    api_key=settings.OPENROUTER_API_KEY,
    base_url=settings.OPENROUTER_BASE_URL
)
qd_client= QdrantDBProvider(settings.QDRANT_URL, settings.VECTOR_SIZE)
qd_client.connect()


if not qd_client.is_collection_exist(collection_name=settings.QDRANT_ITEMS_COLLECTION_NAME):
        qd_client.create_collections(collection_name=settings.QDRANT_ITEMS_COLLECTION_NAME)
        data_to_embed, text_to_embed= get_items_data()
        embeddings= get_embedding_batch(text_list=text_to_embed,
                                        embed_client=embed_client,
                                        embedding_model=settings.EMBEDDING_MODEL,
        )
        pointstruct=[]
        i=1
        for embedding , data in zip(embeddings,data_to_embed):
            pointstruct.append(
                PointStruct(
                    id=i,
                    vector={
                        "embedding": embedding,
                        "bm25": Document(
                            text=data["description"],
                            model="qdrant/bm25"
                        )
                    },
                    payload=data
                )
            )
            i+=1
        qd_client.batch_insert(
                collection_name=settings.QDRANT_ITEMS_COLLECTION_NAME,
                pointstruct=pointstruct
        )
        qd_client.create_indexing(collection_name=settings.QDRANT_ITEMS_COLLECTION_NAME, field_name="parent_asin")

if not  qd_client.is_collection_exist(collection_name=settings.QDRANT_REVIEWS_COLLECTION_NAME):
        qd_client.create_collections(collection_name=settings.QDRANT_REVIEWS_COLLECTION_NAME)
        data_to_embed, text_to_embed_reviews = get_reviews_data(qd_client.client)
        embedding_reviews=get_embedding_batch(text_list=text_to_embed_reviews,
                                        embed_client=embed_client,
                                        embedding_model=settings.EMBEDDING_MODEL,
        )
        point_struct=[]
        i= 1
        for embedding,data in zip(embedding_reviews,data_to_embed):
            if embedding and data:
                point_struct.append(
                    PointStruct(
                        id=i,
                        vector={
                            "embedding": embedding
                        },
                        payload={
                            "text": data["preprocessed_data"],
                            "parent_asin": data["parent_asin"]
                        }
                    )
                )
                i +=1
        print("Start inserting in qdrant")
        qd_client.batch_insert(
                        collection_name=settings.QDRANT_REVIEWS_COLLECTION_NAME,
                        pointstruct=point_struct
                )
        qd_client.create_indexing(collection_name=settings.QDRANT_REVIEWS_COLLECTION_NAME, field_name="parent_asin")


