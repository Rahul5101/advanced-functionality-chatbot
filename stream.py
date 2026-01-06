# main.py

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import time
import json
import re
import os

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from multilingual_pipeline.language_detection import detect_language
from multilingual_pipeline.conversion import translation, output_converison
from milvus_database.milvus_loading import loading_milvus
from streaming.step_1_llm_with_stream import main


# ------------------- FASTAPI SETUP -------------------

app = FastAPI(title="Gemini RAG Streaming API")

origins = [
    "http://localhost",
    "http://localhost:3000",
    "https://km-income-tax-dot-knowledge-minor.el.r.appspot.com/",
    "*",  # for dev, restrict in prod
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------- MODELS -------------------

class QuestionRequest(BaseModel):
    question: str


# ------------------- STREAM ENDPOINT (POST) -------------------

@app.post("/stream")
async def stream(request: QuestionRequest):
    """
    POST endpoint for streaming responses.
    The client sends a JSON body: { "question": "..." }
    The server streams the response incrementally via Server-Sent Events (SSE).
    """

    # start_time = time.time()
    user_question = request.question
    print(f"🔹 Incoming query: {user_question}")

    db_load = loading_milvus()
    
    async def event_generator():
        start_time = time.time()
        async for chunk in main(query=user_question, detected_lang="en"):
            print(chunk, end="")
            elapsed_time = time.time() - start_time
            print("Total Time: ",elapsed_time)
            yield chunk

    # elapsed_time = time.time() - start_time
    # print("Total Time: ",elapsed_time)

    # Return SSE stream
    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ------------------- HEALTH CHECK -------------------

@app.get("/")
async def root():
    return {"message": "Gemini Streaming RAG API is live 🚀"}
