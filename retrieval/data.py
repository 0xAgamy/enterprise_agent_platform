import pandas as pd
def _prerocess_description(row):
    return f"{row["title"]} {' '.join(row["features"])}"


def _extract_first_large_image(row):
    return row["images"][0].get("large","")


df_items= pd.read_json("data/meta_Electronics_2022_2023_with_category_rating_100_samples_1000.jsonl", lines=True)
df_items["description"]= df_items.apply(_prerocess_description,axis=1)
df_items["image"]=df_items.apply(_extract_first_large_image,axis=1)
data_to_embed= df_items[["description","image","rating_number","price","average_rating","parent_asin"]].to_dict(orient="records")

df=pd.DataFrame(data_to_embed)
df.to_json("data/data.json", orient='records',lines=True)