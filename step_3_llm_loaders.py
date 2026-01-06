# --- Imports ---
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
from persistant_memory.loading_and_saving_chat import save_chat_turn, init_db,get_unique_query_count
from persistant_memory.load_chat_history import load_chat_conversation,retrive_from_redis
import sqlite3          
from caching_hisotry.caching.redis_semantic_cache import upsert_rag_response,simple_id_generator,cache_rag,create_index_if_not_exists,refresh_redis_from_sqlite
DB_PATH = "chat_history.db"
init_db()
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
K_THRESHOLD = 23
load_dotenv()       
id_gen = simple_id_generator()
create_index_if_not_exists()
# Legal document generator
from src.legal_generator import generate_legal_text, save_to_docx, save_to_pdf
from langchain_google_genai import (
    ChatGoogleGenerativeAI,
    GoogleGenerativeAIEmbeddings
)



load_dotenv()

GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GOOGLE_API_KEY not found in .env")


def llm_detect_intent(query: str) -> str:
    """
    Uses a lightweight LLM to classify intent:
    - GENERATION
    - QA
    """

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0,
        max_output_tokens=50
    )

    prompt = f"""
You are an intent classification system.

Classify the user query into exactly ONE of the following intents:

1. GENERATION – User wants to draft, create, or prepare a legal document
2. QA – User wants information, explanation, or guidance

Rules:
- If the query asks "what is", "how does", "explain", it is QA
- If the query asks to draft or prepare a document, it is GENERATION
- Return ONLY valid JSON
- No explanations, no markdown

User Query:
{query}

Output:
{{
  "intent": "",
  "confidence": 0.0
}}
"""

    try:
        response = llm.invoke(prompt)
        raw = response.content.strip()

        parsed = json.loads(raw)
        intent = parsed.get("intent", "QA")
        confidence = parsed.get("confidence", 0.0)

        print(f"🤖 LLM Intent: {intent} | Confidence: {confidence}")
        return intent

    except Exception as e:
        print(f"⚠️ Intent detection failed: {str(e)}")
        return "QA"


def smart_intent_router(query: str) -> str:
    """
    Fast rules + LLM fallback (recommended)
    """

    q = query.lower()

    # Obvious QA
    if re.match(r"^(what|how|why|explain|define)\b", q):
        return "QA"

    # Obvious generation
    if re.search(r"\b(draft|prepare|write|generate|create)\b", q):
        return "GENERATION"

    # Otherwise ask LLM
    return llm_detect_intent(query)


def safe_json_parse(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError("LLM output is not valid JSON")


async def main(query: str, detected_lang: str = "en",session_id = "defaut_session"):
    """
    Routes user query:
    - GENERATION → Legal document drafting
    - QA → RAG pipeline
    """

    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print(f"Detected Language: {detected_lang}")
    print(f"{'='*60}\n")

    # --------------------------------------------------
    # STEP 0: INTENT ROUTING (LLM BASED)
    # --------------------------------------------------
    intent = smart_intent_router(query)

    # --------------------------------------------------
    # PATH 1: LEGAL DOCUMENT GENERATION
    # --------------------------------------------------
    if intent == "GENERATION":
        print("🔨 Routing to LEGAL GENERATION pipeline")

        try:
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

        except Exception as e:
            return {
                "intent": "GENERATION",
                "bold_words": [],
                "meta_data": [],
                "response": f"Error generating document: {str(e)}",
                "follow_up": None,
                "table_data": [],
                "ucid": "LEGAL_01"
            }

    # --------------------------------------------------
    # PATH 2: QA (RAG PIPELINE)
    # --------------------------------------------------
    print("Loading embedding model and LLM...")

    # Load model configuration
    config = load_config()
    em_model_name = config['embedding']['google']['model_name']
    llm_model_name = config['llm']['google']['model_name']

    # Initialize embedding model
    embedding_model = GoogleGenerativeAIEmbeddings(model=em_model_name)
    query_vector = embedding_model.embed_query(query)

    print(f"\n[1] Checking Cache for Query: {query}")
        

    cache_lookup = cache_rag(query,query_vector)
    cache_answer = retrive_from_redis(cache_lookup)
    if cache_answer:
        # increment_hit_count(session_id, query)
        print("Final output prepared.", cache_answer)
        save_chat_turn(
            session_id=session_id,
            question=query,
            answer_dict=cache_answer
        )
        return cache_answer
    
    print("🔍 CACHE MISS! Starting full RAG pipeline (Milvus + Rerank + Gemini)...")
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

    # deduped_meta_data = []
    # for m in all_meta_data:
    #     file_name = m.get("source", "").strip()
    #     if "_" in file_name:
    #         file_name = file_name.rsplit("_", 1)[0].strip()
    #     m["source"] = file_name
    #     key = (file_name, m.get("page"))
    #     if key not in seen_files_pages:
    #         deduped_meta_data.append(m)
    #         seen_files_pages.add(key)
    # all_meta_data = deduped_meta_data

    # Step 4: Combine LLM outputs
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
        answer_dict=output
    )

    current_cnt = get_unique_query_count()

    if current_cnt < K_THRESHOLD:
        upsert_rag_response(output, query, query_vector, id_gen)
    elif current_cnt % K_THRESHOLD == 0:
        refresh_redis_from_sqlite(limit=5)
    
    return output
