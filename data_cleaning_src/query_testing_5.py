# from chunking_and_embedding_3 import vectorstore

# # Example query
# query_text = "Definition of child in Bharatiya Nyaya Sanhita"

# # Get top 3 most similar chunks
# results = vectorstore.similarity_search(query_text, k=3)

# for i, doc in enumerate(results):
#     print(f"--- Result {i+1} ---")
#     print("Text:", doc.page_content)
#     print("Metadata:", doc.metadata)



from pymilvus import Collection,connections
import numpy as np
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# collection = Collection("nyaya_sanhita")

# Connect to Milvus
connections.connect("default", host="localhost", port="19530")

collection_name = "nyaya_sanhita"
collection = Collection(collection_name)

# Print schema
print("Collection name:", collection.name)
print("Fields in collection:")
for field in collection.schema.fields:
    print(f"- {field.name} ({field.dtype})")

# Optional: check number of vectors inserted
print("Number of entities in collection:", collection.num_entities)

# Suppose you already have the embedding for your query
embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")
query_embedding = embeddings.embed_query("Definition of child in Bharatiya Nyaya Sanhita")

search_params = {"metric_type": "IP", "params": {"nprobe": 10}}
results = collection.search(
    data=[query_embedding],
    anns_field="embedding",
    param=search_params,
    limit=3,
    expr=None
)

for hits in results:
    for hit in hits:
        print(f"ID: {hit.id}, distance: {hit.distance}")

