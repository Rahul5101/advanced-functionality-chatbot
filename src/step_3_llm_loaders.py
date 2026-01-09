import os
import json
import re
import time
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.output_parsers import StrOutputParser
from multilingual_pipeline.conversion import output_converison
from src.step_4_processing import process_file
from src.utils import load_config
from multilingual_pipeline.conversion import output_converison
# from url_integration.gcs_url import generate_signed_url
from src.step_7_utility import escape_inner_quotes, replace_links
from persistant_memory.loading_and_saving_chat import save_chat_turn, init_db,get_unique_query_count,search_history_semantic
from caching_hisotry.caching.redis_semantic_cache import upsert_rag_response,simple_id_generator,cache_rag,create_index_if_not_exists,refresh_redis_from_sqlite
from persistant_memory.load_chat_history import load_chat_conversation,retrive_from_redis
from complaint_generator.legal_generator import generate_legal_text, save_to_docx, save_to_pdf
from complaint_generator.generator_script import llm_detect_intent
DB_PATH = "chat_history.db"
import sqlite3          
init_db()
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
K_THRESHOLD = 17
load_dotenv()       
id_gen = simple_id_generator()
create_index_if_not_exists()
# Legal document generator

load_dotenv()

async def main(query: str, detected_lang: str = "en",session_id = "defaut_session"):

    intent = llm_detect_intent(query)
    if intent == "GENERATION":
        print(" Routing to LEGAL GENERATION pipeline")

        
        legal_text = generate_legal_text(query)

        if detected_lang not in ["en", "hi", "mr", "te"]:
            detected_lang = "en"

        legal_text_translated = output_converison(
            legal_text, detected_lang
        )

        save_to_docx(legal_text, "generated_complaint.docx")
        save_to_pdf(legal_text, "generated_complaint.pdf")

        return {
            "intent": "GENERATION",
            "bold_words": [],
            "meta_data": [],
            "response": legal_text_translated,
            "follow_up": None,
            "table_data": [],
            "ucid": "LEGAL_01"
        }


    print("Loading embedding model and LLM...")

    # Load model configuration
    config = load_config()
    em_model_name = config['embedding']['google']['model_name']
    embedding_model = GoogleGenerativeAIEmbeddings(model=em_model_name)
    query_vector = embedding_model.embed_query(query)

    print(f"\n[1] Checking Cache for Query: {query}")
        

    try:
        cache_lookup = cache_rag(query, query_vector)
        cache_answer = retrive_from_redis(cache_lookup)
    except Exception as e:
        # Log the error but don't stop the execution
        print(f"⚠️ Redis Cache Error (Index might be missing): {e}")
        cache_answer = None
    if cache_answer is not None:
        print("Final output prepared.", cache_answer)
        save_chat_turn(
            session_id=session_id,
            question=query,
            answer_dict=cache_answer,
            query_vector=query_vector
        )
        curr_cnt = get_unique_query_count()
        if curr_cnt % K_THRESHOLD == 0:
            refresh_redis_from_sqlite(limit=5)
        return cache_answer
    
    # if query is not found in cache proceed with sqlite
    history_response = search_history_semantic(query_vector, proximity_threshold=0.90)
    if history_response:
        print(f" SQLite Semantic Hit! (Sim: {history_response['similarity']:.2f})")
        print("complete response:",history_response["answer"])
        save_chat_turn(
            session_id=session_id,
            question=query,
            answer_dict=history_response["answer"],
            query_vector=query_vector
        )
        curr_cnt = get_unique_query_count()
        if curr_cnt % K_THRESHOLD == 0:
            refresh_redis_from_sqlite(limit=5)
        return history_response["answer"]
    
    print(" CACHE MISS! Starting full RAG pipeline (Milvus + Rerank + Gemini)...")
    chat_history = load_chat_conversation(session_id=session_id,last_n=4)
    tasks = process_file(
        query=query,
        embedding_model=embedding_model,
        chat_history = chat_history
    )
    
    results=[tasks]
    per_file_responses = [r for r in results if r]
    # Step 2: Filter irrelevant responses
    irrelevant_pattern = re.compile(r"(does not provide relevant information|answer is not available)", re.IGNORECASE)
    
    # Step 3: Deduplicate metadata
    all_meta_data = []
    seen_files_pages = set()
    for r in per_file_responses:
        all_meta_data.extend(r["metadata"])

 
    complete_response = "\n\n".join([r["response"] for r in per_file_responses])

    print("complete response: ",complete_response)
    bold_words = list(set(re.findall(r"\*\*(.*?)\*\*", complete_response)))

    # Step 5: Replace links and escape quotes
    # html_text = replace_links(complete_response, all_meta_data)
    # clean_output = escape_inner_quotes(html_text.strip())

    # Convert to dict (your JSON format)
    translated_output = json.loads(complete_response)
    explanation_and_summary = f"{translated_output.get('Explanation')}\n\n**Summary:**\n{translated_output.get('Summary')}"
    follow_up_question = translated_output.get("Follow_up")
    table_data = translated_output.get("table_data")

    # Step 6: Translation
    if detected_lang not in ["en", "hi", "mr", "te"]:
        detected_lang = "en"

    explanation_translated = output_converison(explanation_and_summary, detected_lang)
    follow_up_translated = output_converison(follow_up_question, detected_lang)
    table_data_translated = output_converison(table_data, detected_lang)

    # Step 7: Final output dict
    output = {
        "bold_words": bold_words,
        "meta_data": all_meta_data,
        "response":  explanation_translated ,
        "follow_up": follow_up_translated,
        "table_data": [table_data_translated],
        "ucid": "99_18"  # example unique ID
    }
    print("Final output prepared.", output)
    save_chat_turn(
        session_id=session_id,
        question=query,
        answer_dict=output,
        query_vector=query_vector
    )

    current_cnt = get_unique_query_count()

    if current_cnt < K_THRESHOLD:
        upsert_rag_response(output, query, query_vector, id_gen)
    elif current_cnt % K_THRESHOLD == 0:
        refresh_redis_from_sqlite(limit=5)
    
    return output
