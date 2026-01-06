import os
import re
import json
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from multilingual_pipeline.conversion import output_converison
from streaming.step_2_processing_with_stream import process_file_stream
from src.utils import load_config

load_dotenv()


async def main(query: str, detected_lang: str = "en"):
    """
    Streaming version of the RAG main pipeline.
    Streams Gemini's output live, while handling:
      - Embeddings & retrieval
      - Translation
      - Bold word extraction
      - Metadata accumulation
    """

    print("🔹 [Streaming RAG] Processing query:", query)

    # Step 1: Load configuration and embedding model
    config = load_config()
    em_model_name = config["embedding"]["google"]["model_name"]
    embedding_model = GoogleGenerativeAIEmbeddings(model=em_model_name)

    # Step 2: Initialize metadata and output accumulators
    meta_data_accum = []
    accumulated_text = ""

    # Step 3: Stream the LLM response token by token
    async for chunk in process_file_stream(query=query, embedding_model=embedding_model):
        if not chunk:
            continue

        # Check for completion signal
        if chunk.strip().startswith("data: [DONE]"):
            break

        # Extract clean text token
        text_part = chunk.replace("data:", "").strip()
        if not text_part:
            continue

        # Accumulate response
        accumulated_text += text_part + " "

        # Live bold word detection
        bold_words = list(set(re.findall(r"\*\*(.*?)\*\*", accumulated_text)))

        # Step 4: Translation (on the fly)
        if detected_lang not in ["en", "hi", "mr", "te"]:
            detected_lang = "en"

        translated_chunk = output_converison(text_part, detected_lang)

        # Step 5: Yield partial response chunk as SSE
        sse_data = {
            "type": "token",
            "content": translated_chunk,
            "bold_words": bold_words,
        }
        yield f"data: {json.dumps(sse_data, ensure_ascii=False)}\n\n"

    # Step 6: After streaming ends — send metadata + full text
    bold_words_final = list(set(re.findall(r"\*\*(.*?)\*\*", accumulated_text)))

    # Translate the full accumulated response
    translated_full = output_converison(accumulated_text.strip(), detected_lang)

    final_payload = {
        "type": "final",
        "full_response": translated_full,
        "bold_words": bold_words_final,
        "meta_data": meta_data_accum,  # optional; fill from Milvus if needed
        "ucid": "99_18",
    }

    yield f"data: {json.dumps(final_payload, ensure_ascii=False)}\n\n"
    yield "data: [DONE]\n\n"

