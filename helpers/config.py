from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import ValidationError

class Settings(BaseSettings):
    APP_NAME:str
    APP_VERSION:str


    ##Qdrant
    QDRANT_URL:str
    QDRANT_ITEMS_COLLECTION_NAME:str
    QDRANT_REVIEWS_COLLECTION_NAME:str

    ##Postgres
    DATABASE_URL:str

    ###COHERE
    COHERE_API_KEY:str
    COHERE_BASE_URL:str
    COHERE_EMBEDDING_MODEL:str
    COHERE_RERANKING_MODEL:str

    ###OPENROUTER
    OPENROUTER_BASE_URL:str
    OPENROUTER_API_KEY:str
    EMBEDDING_MODEL:str
    VECTOR_SIZE:int

    ### OLLAMA

    OLLAMA_BASE_URL:str
    OLLAMA_API_KEY:str
    OLLAMA_MODEL_NAME:str

    ### Streamlit
    API_URL:str

    
    model_config = SettingsConfigDict(env_file=".env")


def get_settings():
    try:
        return Settings()
    except ValidationError as e:
        print("Missing required environment variables")
        raise e