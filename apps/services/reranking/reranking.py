from cohere import ClientV2
from typing import List , Dict

class Reranking:
    def __init__(self, api_key, ranking_model):
        self.api_key= api_key
        self.reanking_model= ranking_model
        self.client= self._get_client()

    def _get_client(self):
        return ClientV2(api_key=self.api_key)

    def get_ranking(self, query:str, docs:List[Dict], term:str, k:int):
            return self.client.rerank(
                model=self.reanking_model,
                query=query,
                documents=[doc[term] for doc in docs],
                top_n=k,
            )
            

        