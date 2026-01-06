# milvus_database/milvus_client.py
# from msilib import schema
from pymilvus import (
    connections,
    utility,
    FieldSchema,
    CollectionSchema,
    DataType,
    Collection,
    MilvusClient
)
from milvus_database.config import DB
import uuid
from langchain_core.documents import Document

class MilvusDB:
    def __init__(self, client_path=None):
        self.client_path = client_path
        connections.connect(
            alias="default",
            host='localhost',  # to connect to VM '34.100.163.108' / to run in VM 'milvus-standalone' / to run in local with docker 'localhost'
            port='19530',  # Milvus port exposed by your container
            user='root',  # If authentication is enabled
            password='Milvus'  # If authentication is enabled
        )
        self.model = MilvusClient(
            uri="http://localhost:19530",  # to connect to VM '34.100.163.108:19530' / to run in VM 'milvus-standalone' / to run in local with docker 'localhost'
            token="root:Milvus"  # username:password format
        )


        # self.client_path = client_path
        # alias = "default"

        # # ✅ Only connect if not already connected
        # existing_conns = [c[0] for c in connections.list_connections()]
        # if alias not in existing_conns:
        #     connections.connect(
        #         alias=alias,
        #         host='34.93.179.107',
        #         port='19530',
        #         user='root',
        #         password='Milvus'
        #     )
        #     print(f"Connected to Milvus at 34.93.179.107:19530")
        # else:
        #     print(f"Milvus connection '{alias}' already exists — skipping reconnect.")

        # # Initialize MilvusClient
        # self.model = MilvusClient(
        #     uri="http://34.93.179.107:19530",
        #     token="root:Milvus"
        # )

    def load_db(self):
        self.create_milvus_collection_if_not_exists()
        print("Milvus loaded in memory")
        return self.model

    from pymilvus import DataType

    def create_milvus_collection_if_not_exists(self):
        try:
            if self.model.has_collection(DB.milvus_collection_name):
                print(f"{DB.milvus_collection_name} collection Exists")
                return True

            print(f"Creating Collection: {DB.milvus_collection_name}")
            schema = self.model.create_schema(enable_dynamic_field=True)
            schema.add_field("uuid_id", DataType.VARCHAR, max_length=65, is_primary=True)
            schema.add_field("chapter", DataType.VARCHAR, max_length=500)
            schema.add_field("chapter_title", DataType.VARCHAR, max_length=500)
            schema.add_field("section", DataType.VARCHAR, max_length=50)
            schema.add_field("section_title", DataType.VARCHAR, max_length=500)
            schema.add_field("text", DataType.VARCHAR, max_length=5000)
            schema.add_field("vector", DataType.FLOAT_VECTOR, dim=3072)

            print("inside")

            index_params = self.model.prepare_index_params()
            index_params.add_index(
                field_name="vector",
                metric_type="COSINE",
                index_type="HNSW",
                index_name="vector_hnsw",
                params={"M": 16, "efConstruction": 200}
            )
            print("inside1")


            self.model.create_collection(
                DB.milvus_collection_name,
                schema=schema,
                index_params=index_params,
                consistency_level="Strong"
            )

            print("inside2")

            print(f"✅ Collection {DB.milvus_collection_name} created successfully")

        except Exception as e:
            print(f"Error creating Milvus collection: {e}")
            return False


    def drop_collection(self):
        """Drops a specified collection if it exists."""
        try:
            if utility.has_collection(DB.milvus_collection_name):
                utility.drop_collection(DB.milvus_collection_name)
                print(f"✅ Dropped collection: {DB.milvus_collection_name}")
            else:
                print(f"⚠️ Collection {DB.milvus_collection_name} does not exist.")
        except Exception as e:
            print(f"Error dropping collection '{DB.milvus_collection_name}': {e}")

    def create_partition_if_not_exists(self, collection_name, partition_name):
        """Creates a partition for a table if it doesn't exist"""
        try:
            if not self.model.has_partition(collection_name, partition_name):
                print(f'Creating partition {partition_name}')
                self.model.create_partition(
                    collection_name=collection_name,
                    partition_name=partition_name,
                )
                print(f"Created partition {partition_name} in collection {collection_name}")
        except Exception as e:
            print(f"Error creating partition for table {partition_name}: {e}")

    def insert_data(self, partition_name, data):
        try:
            collection_name = DB.milvus_collection_name

            self.create_partition_if_not_exists(collection_name, partition_name)

            return self.model.insert(
                collection_name=collection_name,
                data=data,
                partition_name=partition_name
            )
        except Exception as e:
            print(f"Error inserting data: {e}")
            return None

    def release_partitions(self, collection_name, partition_names):
        """Releases partitions from memory"""
        try:
            self.model.release_partitions(
                collection_name=collection_name,
                partition_names=partition_names
            )
        except Exception as e:
            print(f"Error releasing partitions: {e}")

    def drop_partition(self, collection_name, partition_name):
        """Drops a partition from a collection"""
        try:
            # First release the partition
            self.release_partitions(collection_name, [partition_name])

            # Then drop it
            self.model.drop_partition(
                collection_name=collection_name,
                partition_name=partition_name
            )
        except Exception as e:
            print(f"Error dropping partition: {e}")

    # --- New method for your JSON format ---
    def insert_json_data(self, partition_name, data_list, embedding_model=None):
        """
        Insert documents from your JSON into Milvus with proper metadata and embeddings.

        Args:
            partition_name: Milvus partition to insert into
            data_list: List of JSON items with keys:
                       chapter, chapter_title, section, section_title, section_desc
            embedding_model: Optional embedding model to generate vectors for section_desc
        """
        try:
            collection_name = DB.milvus_collection_name
            self.create_partition_if_not_exists(collection_name, partition_name)

            insert_data = {
                "uuid_id": [],
                "chapter": [],
                "chapter_title": [],
                "section": [],
                "section_title": [],
                "section_desc": [],
                "vector": []
            }

            for item in data_list:
                desc = item.get("section_desc", "").strip()
                if not desc:
                    continue  # skip empty sections

                # Generate embedding vector if model provided
                vector = embedding_model.embed_query(desc) if embedding_model else [0.0] * 3072

                insert_data["uuid_id"].append(str(uuid.uuid4()))
                insert_data["chapter"].append(item.get("chapter", ""))
                insert_data["chapter_title"].append(item.get("chapter_title", ""))
                insert_data["section"].append(item.get("section", ""))
                insert_data["section_title"].append(item.get("section_title", ""))
                insert_data["section_desc"].append(desc)
                insert_data["vector"].append(vector)

            self.model.insert(
                collection_name=collection_name,
                data=insert_data,
                partition_name=partition_name
            )
            print(f"✅ Inserted {len(insert_data['uuid_id'])} items into {collection_name}/{partition_name}")

        except Exception as e:
            print(f"Error inserting JSON data: {e}")
