from milvus_database.config import DB
from milvus_database.factory_client import MilvusDB
from src.step_3_llm_loaders import main
import os
from dotenv import load_dotenv
load_dotenv()
import asyncio
import time
from milvus_database.milvus_loading import loading_milvus
print("testing")
start = time.time()
# loading_milvus()
session_id = "test_session01"
# query = "hi my name is rahul gupta and i'm a AI Engineer and tell me what is bhartiya nyaya sanhita?"
# query = "as of my previous chat can once again brief me about that"
query = "generate a civil complaint for me"
# query = "what are the different classes of criminal courts"
# query = "what is my name and what I'm?"
# query = "what is my profession?"
# query = "tell me about the Territorial divisions?"
# query = "tell me about the CONSTITUTION OF CRIMINAL COURTS AND OFFICES ?"
# query = "what is the purpose of this Sanhita ?"
# query = "tell me about the Trial of offences under Bharatiya Nyaya Sanhita"
# query = "how's the offence under bhartiya sanhita has investigated"
print("query: ",query)
response = asyncio.run(main(query=query,session_id=session_id))
elapsed_time = time.time() - start
print("Total time", elapsed_time)

