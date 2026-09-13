from openai import OpenAI
class Embedding:
    def __init__(self,api_key, base_url, model_name):
        self.api_key= api_key
        self.base_url= base_url
        self.model_name= model_name
        self.embed_client= self._get_client()

    def _get_client(self):
        return OpenAI(
                    base_url=self.base_url,
                    api_key=self.api_key
                )

    def get_embeddings(self, text):
        response= self.embed_client.embeddings.create(
                    input= text,
                    model=self.model_name,
                    encoding_format="float"
                )
        return response.data[0].embedding
    