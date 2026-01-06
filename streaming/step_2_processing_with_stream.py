# step_4_processing.py
from pymilvus import connections
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from vertexai.preview.language_models import TextGenerationModel
from src.step_5_prompt import prompt
from src.step_6_reranker import rerank_with_google
from milvus_database.milvus_db import vector_search
from milvus_database.config import DB
import os
import time
import json
import asyncio
from vertexai.generative_models import GenerativeModel
from src.llm_config import GENERATION_CONFIG,safety_settings

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.join(os.getcwd(), "service-account.json")


# ------------------- STREAMING VERSION -------------------
async def process_file_stream(query, embedding_model):
    """
    Async generator for streaming Gemini responses via SSE.
    """
    try:
        print(f"\n[Streaming Query]: {query}")

        # Step 1: Embed query
        query_vector = embedding_model.embed_query(query)

        # Step 2: Vector search in Milvus
        results = vector_search(
            collection_name=DB.milvus_collection_name,
            partition_name=DB.default_partition,
            query_vectors=query_vector,
            num_results=30,
        )

        hits = results[0] if results else []

        # Step 3: Prepare documents
        docs = []
        for hit in hits:
            entity = hit["entity"]
            text = entity.get("text", "")
            doc = Document(
                page_content=text,
                metadata={
                    "chapter": entity.get("chapter"),
                    "chapter_title": entity.get("chapter_title"),
                    "section": entity.get("section"),
                    "section_title": entity.get("section_title"),
                    "score": hit.get("distance"),
                },
            )
            docs.append(doc)

        # Step 4: Rerank top documents
        project_id = "km-judisasory"
        docs = rerank_with_google(query, docs, project_id)[:10]

        # Step 5: Build context
        context_chunks = []
        for doc in docs:
            md = doc.metadata
            meta_line = f"[Meta: chapter={md['chapter']}, chapter_title={md['chapter_title']}, section={md['section']}, section_title={md['section_title']}]"
            context_chunks.append(f"{doc.page_content}-->{meta_line}\n\n")

        context = "\n\n".join(context_chunks)

        formatted_prompt = prompt.format(context=context, question=query)
        model = GenerativeModel("gemini-2.5-flash")

        # Step 6: Stream from Gemini
        stream = model.generate_content(
            formatted_prompt,
            generation_config=GENERATION_CONFIG,
            safety_settings=safety_settings,
            stream=True,
        )

        # Step 7: Yield token-by-token output
        for chunk in stream:
            if hasattr(chunk, "text") and chunk.text:
                yield f"data: {chunk.text}\n\n"

        # Final event
        yield "data: [DONE]\n\n"

    except Exception as e:
        yield f"data: [Error] {str(e)}\n\n"