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
session_id = "test_session02"
# query = "hi my name is rahul gupta and i'm a AI Engineer and tell me what is bhartiya nyaya sanhita?"
# query = "as of my previous chat can once again brief me about that"
# query = "generate a civil complaint for me"
# query = "what are the different classes of criminal courts"
# query = "hi my name is rahul gupta and keep my name in mind "
# query = "do you know my name is? "
# query = "tell me about court of magistrates?"
# query = "define the executives of judicial magistrates?"
# query="tell me my name?"
query = "tell me about the Territorial divisions?"
# query = "tell me about the CONSTITUTION OF CRIMINAL COURTS AND OFFICES ?"
# query = "tell me about court of judicary megistrate?" 
# query = "what is the purpose of this Sanhita ?"
# query = "what does the court of judical migistrate do? "
# query = "how does the court of judical migistrate do?"
# query = "tell me about the Trial of offences under Bharatiya Nyaya Sanhita"
# query = "how's the offence under bhartiya sanhita has investigated"
# query = "how we investigate the offence for bhartiya sanhita"
# query = "what is Territorial divisions in bhartiya sanhita?"  
# query = "tell me about the Act of a child above seven and under twelve years of age of immature understanding"
print("query: ",query)
response = asyncio.run(main(query=query,detected_lang="en",session_id=session_id))
elapsed_time = time.time() - start
print("Total time", elapsed_time)

