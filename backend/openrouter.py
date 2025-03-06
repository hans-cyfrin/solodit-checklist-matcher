import os
import requests
import random
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# List of available models
AVAILABLE_MODELS = [
    "anthropic/claude-3.7-sonnet",
    "anthropic/claude-3.5-sonnet",
    "anthropic/claude-3.7-sonnet:thinking",
    "google/gemini-2.0-pro-exp-02-05:free",
    "google/gemini-flash-1.5-8b",
    "google/gemini-2.0-flash-lite-001",
    "deepseek/deepseek-r1",
    "deepseek/deepseek-r1-distill-llama-70b",
    "deepseek/deepseek-r1-distill-qwen-32b",
    "x-ai/grok-2-1212",
    "meta-llama/llama-3.3-70b-instruct",
]

def chat_completion(message: str, model: Optional[str] = None) -> Optional[str]:
    """
    Send a chat completion request to OpenRouter.
    
    Args:
        message (str): The message to send
        model (str, optional): The model to use. If not provided, uses the OPENROUTER_MODEL env var or default
    
    Returns:
        Optional[str]: The response text or None if the request failed
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("Error: No OpenRouter API key found in environment variables")
        return None

    try:
        # Get model from parameter, env var, or use default
        primary_model = model or os.getenv("OPENROUTER_MODEL") or "anthropic/claude-3.7-sonnet"

        # Get 3 random fallback models excluding the primary model
        available_models = [m for m in AVAILABLE_MODELS if m != primary_model]
        fallback_models = random.sample(available_models, min(3, len(available_models)))

        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://github.com/cyfrin/solodit-checklist-matcher",
            "X-Title": "Solodit Checklist Matcher"
        }

        data = {
            "model": primary_model,
            "models": fallback_models,
            "messages": [{"role": "user", "content": message}]
        }

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=60
        )

        response.raise_for_status()
        result = response.json()

        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"].strip()

        return None

    except Exception as e:
        print(f"[OpenRouter] Error: {str(e)}")
        return None
