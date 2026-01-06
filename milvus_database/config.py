from pymilvus import connections, utility
class DB:
    """
    Configuration class for Milvus Database.
    Stores collection name, embedding dimensions, and other DB params.
    """

    # Default collection name (can be overridden in scripts)
    milvus_collection_name: str = "km_judiciary"

    # Embedding dimensions (will be set dynamically after reading FAISS)
    model_dimensions: int = 3072

    # Local Milvus connection parameters
    host: str = "localhost"
    port: str = "19530"
    user: str = "root"
    password: str = "Milvus"

    # Default partition
    default_partition: str = "default"


# Connect to Milvus
connections.connect("default", host="localhost", port="19530")

print(" Connected to Milvus!")

# Check collections
print("Available collections:", utility.list_collections())


print("Current DB: ",DB.milvus_collection_name)