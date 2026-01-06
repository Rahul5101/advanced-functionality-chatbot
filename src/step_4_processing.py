from pymilvus import connections,Collection,utility
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from vertexai.generative_models import GenerativeModel  #issue
from dotenv import load_dotenv
from src.step_5_prompt import prompt
from src.step_6_reranker import rerank_with_google

from src.llm_config import safety_settings, GENERATION_CONFIG

from milvus_database.milvus_db import vector_search
from milvus_database.config import DB


import os
import gc
import time
import json

# --- Environment Setup ---
load_dotenv()
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.join(os.getcwd(), "service-account.json")

def process_file(query, embedding_model,chat_history):
    """
    Match senior's function signature but adapted for JSON-based legal data.
    """
    query_vector = embedding_model.embed_query(query)
    try:
        
        print(f"\n Processing Query: {query}")

        results = vector_search(
            collection_name=DB.milvus_collection_name,
            partition_name=DB.default_partition,
            query_vectors=query_vector,
            num_results=30
        )

        hits = results[0] if results else []

        # Step 3: Build docs
        docs,meta_data = [],[]
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
                    "score": hit.get("distance")
                }
            )
            docs.append(doc)
            meta_data.append(doc.metadata)

        # Step 4: Rerank
        start_time = time.time()
        project_id = "km-judisasory"
        docs = rerank_with_google(query, docs, project_id)[:10]
        print("re ranking time", time.time()-start_time)

        # Step 5: Build context
        context_chunks = []
        for doc in docs:
            md = doc.metadata
            meta_line = f"[Meta: chapter={md['chapter']}, chapter_title={md['chapter_title']}, section={md['section']}, section_title={md['section_title']}]"
            context_chunks.append(f"{doc.page_content}-->{meta_line}\n\n")

        context = "\n\n".join(context_chunks)

        # Step 6: Generate LLM response
        formated_prompt = prompt.format(context=context, question=query,chat_history=chat_history)

        model = GenerativeModel("gemini-2.5-flash")
        result_new = model.generate_content(
            formated_prompt,
            generation_config=GENERATION_CONFIG,
            safety_settings=safety_settings,
        )

        # print("result_new:", result_new)

        response = result_new.candidates[0].content.parts[0].text
        print("\n Response:", response)

        final_output = {
            "query": query,
            "response": response,
            "metadata": meta_data
        }
        # print("💾 Saving new result to Semantic Cache...")
        # upsert_rag_response(
        #     rag_answer=final_output,
        #     query_text = query,
        #     query_vector=query_vector,
        #     id_generator=id_gen
        # )
        return final_output

    except Exception as e:
        print(f" Error processing query: {e}")
        return None

# # --- Example Usage ---
# if __name__ == "__main__":
#     sample_query = "What does Section 1 of Bharatiya Nyaya Sanhita state?"
#     output = process_file(sample_query)
#     if output:
#         print("\n--- Response ---")
#         print(output["response"])
