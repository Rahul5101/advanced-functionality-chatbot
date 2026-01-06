from fastapi import FastAPI,BackgroundTasks,Request
from pydantic import BaseModel
import asyncio
from fastapi.responses import JSONResponse
import time
from src.step_3_llm_loaders import main
from milvus_database.milvus_loading import loading_milvus
import os
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Header
from multilingual_pipeline.language_detection import detect_language
from multilingual_pipeline.conversion import output_converison,translation

import httpx


BASE_DIR = os.getcwd()
app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:3000",
    "https://km-income-tax-dot-knowledge-minor.el.r.appspot.com/",
    "*",  # Use "*" to allow all origins (not recommended in production)
]
# Add CORS middleware to your app
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,            # List of allowed origins
    allow_credentials=True,           # Allow cookies and auth headers
    allow_methods=["*"],              # Allow all HTTP methods
    allow_headers=["*"],              # Allow all headers
)


# Request model: user sends a question
class QuestionRequest(BaseModel):
    question: str
    session_id : str
# # Response model: we respond with JSON
class AnswerResponse(BaseModel):
    answer: str

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/query", response_model=AnswerResponse)
def answer_question(request: QuestionRequest):
    user_question = request.question
    session_id = request.session_id
    start_time = time.time()

    detected_lang = detect_language(user_question)
    print("detected langauge",detected_lang)

    translate_query = translation(detected_lang=detected_lang,user_query=user_question)

    print("translated query: ",translate_query)
    db_load = loading_milvus()
    response_data = asyncio.run(main(query=translate_query,session_id= session_id))
    elapsed_time = time.time() - start_time

    print(f"\nTotal time consumed: {elapsed_time:.2f} seconds")

    return JSONResponse(response_data)



# class CacheUpsertRequest(BaseModel):
#     query: str
#     session_id: str
#     response_data: dict
# # its a background task
# async def update_cache_bg(query: str, response_data: dict):
#     """
#     Sends data to the cache endpoint after the user gets their response.
#     """
#     async with httpx.AsyncClient() as client:
#         try:
#             payload = {
#                 "query": query,
#                 "session_id": "system_sync", 
#                 "response_data": response_data
#             }
#             await client.post("http://127.0.0.1:8000/upsert_cache", json=payload)
#             print(" Background cache update triggered.")
#         except Exception as e:
#             print(f" Background cache update failed: {e}")

# @app.post("/query")
# async def answer_question(request: QuestionRequest, background_tasks: BackgroundTasks):
#     user_question = request.question
#     session_id = request.session_id
#     start_time = time.time()

#     detected_lang = detect_language(user_question)
#     translate_query = translation(detected_lang=detected_lang, user_query=user_question)

   
#     response_data = await main(query=translate_query, session_id=session_id)


#     if response_data.get("source") != "semantic-cache":
#         background_tasks.add_task(update_cache_bg, translate_query, response_data)

#     elapsed_time = time.time() - start_time
#     print(f"\nTotal time consumed: {elapsed_time:.2f} seconds")

#     return JSONResponse(response_data)


# @app.post("/upsert_cache")
# async def upsert_cache(request: CacheUpsertRequest):
#     """
#     The internal endpoint that actually performs the Redis insertion.
#     """
#     from caching_hisotry.caching.redis_semantic_cache import upsert_rag_response, simple_id_generator
#     from langchain_google_genai import GoogleGenerativeAIEmbeddings
    
#     try:
#         embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
#         query_vector = embeddings.embed_query(request.query)
        
#         upsert_rag_response(
#             rag_answer=request.response_data,
#             query_text=request.query,
#             query_vector=query_vector,
#             id_generator=simple_id_generator()
#         )
#         return {"message": "Cache updated successfully"}
#     except Exception as e:
#         print(f"Error in upsert_cache: {e}")
#         return {"message": "Cache update failed", "error": str(e)}
