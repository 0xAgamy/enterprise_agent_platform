from pydantic_settings import BaseSettings, SettingsConfigDict

class Config(BaseSettings):

    API_URL: str = "http://localhost:8000"

    model_config = SettingsConfigDict(env_file="../.env")

config = Config()