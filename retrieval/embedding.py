from tqdm.auto import tqdm
import pandas as pd 
import time
import tiktoken
def get_embedding(text,embed_client,embedding_model):
    response=embed_client.embeddings.create(
        input=[text],
        model=embedding_model,
        encoding_format="float"
    )
    return response.data[0].embedding

def get_embedding_batch(text_list,embed_client,embedding_model,batch_size=1000):
    if len(text_list) <= batch_size:
        response=embed_client.embeddings.create(
        input=text_list,
        model=embedding_model,
        encoding_format="float"
        )
        return [ embedding.embedding  for embedding in response.data]
    
    all_embedding=[]
    counter=1

    for i in tqdm(range(0,len(text_list), batch_size)):
        batch= text_list[i:i + batch_size]
        response=embed_client.embeddings.create(
        input=batch,
        model=embedding_model,
        encoding_format="float"
        )
        all_embedding.extend([ embedding.embedding  for embedding in response.data] )
        counter+=1
    return all_embedding


def get_items_data():
    def _prerocess_description(row):
        return f"{row["title"]} {' '.join(row["features"])}"


    def _extract_first_large_image(row):
        return row["images"][0].get("large","")

    
    df_items= pd.read_json("data/meta_Electronics_2022_2023_with_category_rating_100_samples_1000.jsonl", lines=True)
    df_items["description"]= df_items.apply(_prerocess_description,axis=1)
    df_items["image"]=df_items.apply(_extract_first_large_image,axis=1)
    data_to_embed= df_items[["description","image","rating_number","price","average_rating","parent_asin"]].to_dict(orient="records")
    text_to_embed= [data["description"] for data in data_to_embed]
    return data_to_embed, text_to_embed

def get_reviews_data(qd_client):
    def _preprocess_reviews_data(row):
        return f"{row["title"] } {row['text']}"

    def _token_count(row, model="text-embedding-3-large"):
        encoding= tiktoken.encoding_for_model(model)

        return len(encoding.encode(row["preprocessed_data"]))
    df_reviews= pd.read_json("data/Electronics_2022_2023_with_category_rating_100_sample_1000.jsonl",lines=True)

    payload=qd_client.query_points(
                                collection_name="Amazon_items",
                                limit=1000,
                                with_payload=['parent_asin'],
                                with_vectors=False
                                )   
    parent_asin_list= [  item.payload["parent_asin"] for item in payload.points]
    
    df_reviews_sample= df_reviews[df_reviews["parent_asin"].isin(parent_asin_list)]

    df_reviews_sample["preprocessed_data"]= df_reviews_sample.apply(_preprocess_reviews_data, axis=1)
    df_reviews_sample["preprocessed_data_token_count"] = df_reviews_sample.apply(_token_count,axis=1)

    df_reviews_sample=df_reviews_sample[df_reviews_sample["preprocessed_data_token_count"] < 8192 ]
    
    data_to_embed= df_reviews_sample[["preprocessed_data","parent_asin"]].to_dict(orient="records")
    text_to_embed_reviews= [data["preprocessed_data"] for data in data_to_embed ]

    return data_to_embed, text_to_embed_reviews





