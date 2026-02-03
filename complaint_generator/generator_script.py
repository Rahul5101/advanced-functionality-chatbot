import json
import re
from typing import Literal, Optional
from pydantic import BaseModel

from langchain_ollama import ChatOllama
import os
import requests

MODEL_API = os.getenv("MODEL_API")
EMBED_MODEL = os.getenv("EMBED_MODEL", "qwen3-embedding:0.6b")
LLM_MODEL=os.getenv("LLM_MODEL","qwen2.5:3b-instruct-q8_0")
# OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")


IntentType = Literal["QA", "GENERATION"]
ComplaintType = Literal[
    "HARASSMENT",
    "THEFT",
    "COURT",
    "CONSUMER"
]

class RouterOutput(BaseModel):
    intent: IntentType
    complaint_type: Optional[ComplaintType] = None


def safe_json_parse(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError("Invalid JSON from LLM")


def llm_detect_intent(query: str) -> RouterOutput:
    prompt = f"""
You are an intent classifier.

Decide:
- QA → questions, explanations, law info
- GENERATION → drafting legal documents

If GENERATION, classify complaint type.

Complaint types allowed:
HARASSMENT, THEFT, COURT, CONSUMER

Rules:
- If intent is QA → complaint_type must be null
- If intent is GENERATION → complaint_type must be one of:
  ["HARASSMENT","THEFT","COURT","CONSUMER"]

Query:
"{query}"

Return ONLY valid JSON (no markdown, no extra text).

Examples:
{{"intent": "QA"}}
{{"intent": "GENERATION", "complaint_type": "CONSUMER"}}
"""

    try:
        # response = router_llm.invoke(prompt)
        data = {
            "model": LLM_MODEL,
            "prompt": prompt,
            "options": {
                "temperature": 0,       # lower = more deterministic
                "top_p": 0.9,           # nucleus sampling
                "repeat_penalty": 1.1,  # discourages repetition
                "num_predict": 8192     # max tokens to generate
            }
        }

        print("model hitting api: ",f"{MODEL_API}/api/generate")
        response = requests.post(f"{MODEL_API}/api/generate",prompt,stream=True)
        data = safe_json_parse(response.content)
        return RouterOutput(**data)
    except Exception as e:
        print("[Router Error]", e)
        return RouterOutput(intent="QA")



# import json
# import re
# from typing import Literal, Optional
# from pydantic import BaseModel

# from langchain_ollama import ChatOllama
# import os
# import requests

# MODEL_API = os.getenv("MODEL_API", "http://localhost:11434")
# # EMBED_MODEL = os.getenv("EMBED_MODEL", "qwen3-embedding:0.6b")
# # LLM_MODEL=os.getenv("LLM_MODEL","qwen2.5:3b-instruct-q8_0")
# # LLM_MODEL=os.getenv("LLM_MODEL1","gemma3:1b")
# # LLM_MODEL=os.getenv("LLM_MODEL1","qwen2.5:1.5b-instruct")
# LLM_MODEL=os.getenv("LLM_MODEL1","qwen2.5:1.5b")
# # LLM_MODEL=os.getenv("LLM_MODEL1","qwen2.5:0.5b")   
# # OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434") 


# QueryComplexity = Literal["SIMPLE", "COMPLEX"]
# domainType = Literal["LAW", "TECHNICAL", "FINANCE", "MEDICAL","MATHEMATICS", "GENERAL", "OTHER"]


# class RouterOutput(BaseModel):
#     complexity: QueryComplexity
#     confidence: float
#     reason: str
#     domain: domainType


# def safe_json_parse(text: str):
#     try:
#         return json.loads(text)
#     except json.JSONDecodeError:
#         match = re.search(r"\{.*\}", text, re.DOTALL)
#         if match:
#             return json.loads(match.group())
#         raise ValueError("Invalid JSON from LLM")


# def route_query(query: str) -> RouterOutput:
#     prompt = f"""
# You are a routing classifier for a RAG system.

# Your task is to classify a user query by:
# 1) Complexity
# 2) Domain (knowledge area)

# RULES:
# - If the reason implies basic factual knowledge → complexity MUST be SIMPLE
# - If the reason implies analysis or deep reasoning → complexity MUST be COMPLEX
# - Domain MUST match the reason
# - NEVER contradict your own reason

# Confidence score:
# - this is a number between 0 and 1 decimal number representing.
# - if the complexity is SIMPLE then its confidence is LOW VALUE and if the complexity is COMPLEX then its confidence is HIGH VALUE

# Domain:
# - LAW
# - TECHNICAL
# - FINANCE
# - MEDICAL
# - MATHEMATICS
# - GENERAL
# - OTHER

# Return ONLY valid JSON in this format:
# {{
#   "complexity": "SIMPLE" | "COMPLEX",
#   "confidence": number,
#   "domain": "LAW" | "TECHNICAL" | "FINANCE" | "MEDICAL" | "MATHEMATICS" | "GENERAL" | "OTHER",
#   "reason": "brief justification"
# }}
# anylize the reason you give and find complexity and confidence based on the query justification.

# User query:
# "{query}"
# """


#     try:
#         data = {
#             "model": LLM_MODEL,
#             "prompt": prompt,
#             "format": "json",
#             "options": {
#                 "temperature": 0,
#                 "top_p": 0.9,
#                 "repeat_penalty": 1.1,
#                 "num_predict": 256
#             }
#         }

#         response = requests.post(f"{MODEL_API}/api/generate", json=data, timeout=30)

#         # --- Collect streamed chunks ---
#         fragments = []
#         for line in response.text.strip().splitlines():
#             obj = json.loads(line)
#             if "response" in obj:
#                 fragments.append(obj["response"])

#         # --- Join all fragments into one JSON string ---
#         full_text = "".join(fragments)

#         # --- Parse the complete JSON ---
#         parsed = json.loads(full_text)

#         # return RouterOutput(**parsed)
#         return parsed
#     except Exception as e:
#         print("[Router Error]", e)
#         return RouterOutput(
#             complexity="SIMPLE",
#             confidence=0.5,
#             reason="Fallback due to routing error"
#         )


# route_ans = route_query(
#     "Explain the process of machine learning and its real-world applications."
# )
# print("route is:", route_ans)
# print("type is:", type(route_ans))


# import pandas as pd

# MODELS = [
#     # "qwen2.5:0.5b",
#     "qwen2.5:1.5b",
#     "qwen2.5:1.5b-instruct",
# ]

# QUERIES = [
#     "What is the capital of France?",
#     "Explain ship classification and statutory regulation",
#     "How does compound interest work?",
#     "What are the symptoms of diabetes?",
#     "Solve the equation x^2 - 4x + 4 = 0",
#     "Describe the process of photosynthesis.",
#     "What are the main causes of climate change?",
#     "Explain the theory of relativity.",
#     "How do vaccines work?",
#     "What is quantum computing?",
#     "What are the legal implications of breach of contract?",
#     "Describe the process of cellular respiration.",
#     "What are the different types of machine learning algorithms?",
#     "Explain the significance of the Magna Carta in legal history.",
#     "How does blockchain technology function?",
#     "What are the key principles of constitutional law?",
#     "Describe the water cycle in nature.",
#     "What are the main functions of the human brain?",
#     "Explain the concept of supply and demand in economics.",
#     "What are the different types of renewable energy sources?",
#     "How does the immune system protect the body from pathogens?",
#     "What are the legal rights of tenants in rental agreements?",
#     "Describe the process of DNA replication.",
#     "What are the main components of a computer system?",
#     "Explain the principles of criminal law.",
#     "What are the effects of global warming on ecosystems?",
#     "How does the nervous system transmit signals?",
#     "What are the different types of financial markets?",
#     "Explain the concept of intellectual property law.",
#     "Describe the process of mitosis in cell division.",
#     "Explain the bulking stress and what's its inpact on the heavy materials",
    

#     # add up to 50
# ]

# records = []

# for model in MODELS:
#     LLM_MODEL = model
#     for q in QUERIES:
#         result = route_query(q)

#         records.append({
#             "model": model,
#             "query": q,
#             "complexity": result.get("complexity"),
#             "confidence": result.get("confidence"),
#             "domain": result.get("domain"),
#             "reason": result.get("reason")
#         })

# df = pd.DataFrame(records)
# print(df.head())
