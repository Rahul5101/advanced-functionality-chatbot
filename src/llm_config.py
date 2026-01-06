from vertexai.generative_models import GenerativeModel, Part, SafetySetting
from src.step_5_prompt import prompt

# --- Define Safety Settings ---
safety_settings = [
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE
    ),
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE
    ),
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE
    ),
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE
    ),
]
# --- Define Model Configuration ---
GENERATION_CONFIG = {
    "max_output_tokens": 8192,
    "temperature": 0,
    "top_p": 1,
    "response_mime_type": "application/json",
    "response_schema": {
        "type": "OBJECT",
        "properties": {
            "Explanation": {"type": "STRING"},
            "Summary": {"type": "STRING"},
            "Follow_up": {"type": "STRING"},
            "table_data": {"type": "STRING"},
        },
        "required": ["Explanation", "Summary", "Follow_up","table_data"],
    },
    "thinking_config": {"thinking_budget": 0},
}






