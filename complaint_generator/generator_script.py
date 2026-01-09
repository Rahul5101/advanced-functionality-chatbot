from langchain_google_genai import (
    ChatGoogleGenerativeAI,
    GoogleGenerativeAIEmbeddings
)
import json
import os 
import re
from dotenv import load_dotenv
load_dotenv()
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")



from pydantic import BaseModel
from typing import Literal
import json
class IntentOutput(BaseModel):
    intent: Literal["QA", "GENERATION"]
def parse_with_pydantic(llm_output: str) -> str:
    """
    Parse LLM output using Pydantic model
    """
    # Clean the output
    output = llm_output.strip()
    # Try to extract JSON if present
    import re
    json_match = re.search(r'\{.*\}', output, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group())
            result = IntentOutput(**data)
            return result.intent
        except:
            pass
    # If no JSON, try direct parsing
    output_upper = output.upper()
    if "GENERATION" in output_upper:
        return "GENERATION"
    elif "QA" in output_upper:
        return "QA"
    return "QA"
# Usage in your existing function
def     llm_detect_intent(query: str) -> str:
    """
    Your original function with Pydantic parsing
    """
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0
    )
    prompt = f"""You are an intent classification system.

Your task is to analyze the user query and determine its primary intent.
Classify the query into exactly one of the following categories:
Intent Categories
QA :
Select QA if the user is primarily seeking:
Information, facts, or knowledge
Explanations or clarifications
Definitions or meanings
Reasoning, analysis, or comparisons
Guidance on how or why something works
Answers based on existing knowledge
The goal of a QA query is to understand or retrieve information, not to create new content.

GENERATION :
Select GENERATION if the user is primarily requesting:
Creation of new content
Writing, drafting, or composing text
Templates, prompts, structured outputs, or examples
The goal of a GENERATION query is to produce or modify content.

Decision Rules
Focus on the primary intent, not secondary implications
If the query asks for an answer or explanation → QA
If the query asks to create, generate, or transform content → GENERATION
Do not infer intent beyond what is explicitly requested
Choose one and only one intent

Do not include explanations or additional text
Query: "{query}"
Output must be valid JSON: {{"intent": "QA"}} or {{"intent": "GENERATION"}}"""
    try:
        response = llm.invoke(prompt)
        intent = parse_with_pydantic(response.content)
        return intent
    except:
        return "QA"


# def smart_intent_router(query: str) -> str:
#     """
#     Fast rules + LLM fallback (recommended)
#     """

#     q = query.lower()

#     # Obvious QA
#     if re.match(r"^(what|how|why|explain|define)\b", q):
#         return "QA"
    
#     # Obvious generation
#     if re.search(r"\b(draft|prepare|write|create)\b", q):
#         return "GENERATION"

#     # Otherwise ask LLM
#     return llm_detect_intent(query)

def safe_json_parse(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError("LLM output is not valid JSON")