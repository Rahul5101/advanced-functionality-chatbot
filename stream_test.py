from milvus_database.config import DB
from milvus_database.factory_client import MilvusDB
from streaming.step_1_llm_with_stream import main
import os
from dotenv import load_dotenv
load_dotenv()
import asyncio
import time
from milvus_database.milvus_loading import loading_milvus
print("testing")
start = time.time()
# loading_milvus()
query = "Under what circumstances can a person be tried in India for an offence committed outside the country according to the Bharatiya Nyaya Sanhita?"
print("query: ",query)

async def test():
    async for chunk in main(query=query, detected_lang="en"):
        print(chunk, end="")

response = asyncio.run(test())
elapsed_time = time.time() - start
print("Total time", elapsed_time)

