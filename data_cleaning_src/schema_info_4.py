from pymilvus import Collection, connections

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
