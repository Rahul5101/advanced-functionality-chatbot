from milvus_database.config import DB
import os
from milvus_database.factory_client import MilvusDB
import json
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from uuid import uuid4
from dotenv import load_dotenv
load_dotenv()
from pymilvus import Collection

# Initialize embedding model
embedding_model = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
batch_size = 10  # adjust based on memory and Milvus performance

# Initialize Milvus client
milvus_db = MilvusDB()
milvus_client = milvus_db.load_db()


def insert_json_docs_in_milvus(json_data, partition_name="default", batch_size=128):
    """
    Inserts JSON documents into Milvus in batches, skipping duplicates.
    JSON format keys: chapter, chapter_title, section, section_title, section_desc
    """
    # Load existing texts from Milvus once
    existing_texts = get_existing_texts(partition_name)
    print(f" Found {len(existing_texts)} existing records in Milvus")

    batch = []
    total_docs = 0
    skipped = 0

    print("json data",json_data[0:2])

    for item in json_data:
        
        text = item.page_content.strip()
        chapter = item.metadata.get("chapter", "unknown")
        chapter_title= item.metadata.get("chapter_title", "unknown")
        section = item.metadata.get("section", "unknown")
        section_title = item.metadata.get("section_title", "unknown")

        # section_desc = item.get("section_desc", "").strip()
        

        # Skip if already exists
        if text in existing_texts:
            skipped += 1
            continue

        # Generate embedding
        embedding = embedding_model.embed_query(text)

        # Prepare Milvus record
        record = {
            "uuid_id": str(uuid4()),
            "text": text,
            "chapter": chapter,
            "chapter_title": chapter_title,
            "section": section,
            "section_title": section_title,
            "vector": embedding
        }
        batch.append(record)
        existing_texts.add(text)
        total_docs += 1

        print(" total docs:",total_docs)

        # Insert batch when batch_size is reached
        if len(batch) >= batch_size:
            insert_partition_data_in_collection(partition_name, batch)
            batch = []

    # Insert remaining records
    if batch:
        insert_partition_data_in_collection(partition_name, batch)

    print(f" Finished: Inserted {total_docs} new docs, Skipped {skipped} duplicates.")
    return total_docs, skipped


def get_existing_texts(partition_name):
    """
    Fetches all existing texts from a Milvus partition and returns a Python set.
    """
    from pymilvus import Collection
    collection = Collection(DB.milvus_collection_name)
    collection.load()

    existing_texts = set()
    offset = 0
    limit = 2000  # fetch in chunks to avoid memory issues

    while True:
        res = collection.query(
            expr="",  # no filter
            output_fields=["text"],  # must match Milvus collection field!
            partition_names=[partition_name],
            offset=offset,
            limit=limit
        )
        if not res:
            break
        for r in res:
            existing_texts.add(r["text"])  # 'text' matches Milvus field name
        offset += limit

    return existing_texts



def insert_partition_data_in_collection(partition_name, data):
    """Insert batch data into Milvus partition"""
    collection_name = DB.milvus_collection_name
    if not milvus_client.has_collection(collection_name):
        milvus_client.create_milvus_collection_if_not_exists(collection_name)
    return milvus_db.insert_data(partition_name=partition_name, data=data)


def vector_search(collection_name, partition_name, query_vectors, num_results):
    res = milvus_client.search(
        collection_name=collection_name,
        partition_names=[partition_name],
        data=[query_vectors],
        limit=num_results,
        output_fields=["text", "chapter", "chapter_title", "section", "section_title"]
    )
    return res


def retrieve_all_collections():
    return milvus_client.list_collections()


def unique_results(res):
    seen_texts = set()
    unique_results = []
    for result in res[0]:
        text = result['entity']['section_desc']
        if text not in seen_texts:
            seen_texts.add(text)
            unique_results.append(result)
    return unique_results


def retrieve_collection_schema(collection_name):
    try:
        schema = milvus_client.describe_collection(collection_name)
        print(f"Collection: {schema}")
    except Exception as e:
        print(f"Error retrieving schema for collection '{collection_name}': {e}")


def retrieve_all_data_in_schema(collection_name):
    return milvus_client.get_collection_stats(collection_name=collection_name)


def vector_search_truths(partition_names, query_embeddings):
    try:
        collection_name = DB.milvus_collection_name
        existing_partitions = [
            p for p in partition_names if milvus_db.model.has_partition(
                collection_name=collection_name,
                partition_name=p
            )
        ]
        if not existing_partitions:
            return []

        results = milvus_db.model.search(
            collection_name=collection_name,
            data=query_embeddings,
            limit=40,
            output_fields=["section_desc"],
            partition_names=existing_partitions,
            search_params={"metric_type": "COSINE", "params": {"nprobe": 10}}
        )
        return results

    except Exception as e:
        print(f"Error retrieving partition data: {e}")
        return []


def delete_partition(collection_name, partition_name):
    milvus_db.drop_partition(collection_name=collection_name, partition_name=partition_name)
    print(f"Deleted partition {partition_name} from collection {collection_name}")
