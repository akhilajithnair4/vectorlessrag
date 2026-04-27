import os
from dotenv import load_dotenv

load_dotenv(override=True)

CHAT_HISTORY = "chats.json"


def get_llm():
    from llms.openai_llm import OpenAILLM
    from llms.gemini_llm import GeminiLLM
    from llms.claude_llm import ClaudeLLM
    from llms.ollama_llm import OllamaLLM

    provider = os.getenv("LLM_PROVIDER", "openai")
    if provider == "openai":
        return OpenAILLM(api_key=os.getenv("OPENAI_API_KEY"))
    elif provider == "gemini":
        return GeminiLLM(api_key=os.getenv("GEMINI_API_KEY"), model_name=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
    elif provider == "claude":
        return ClaudeLLM(api_key=os.getenv("CLAUDE_API_KEY"))
    elif provider == "ollama":
        return OllamaLLM(model=os.getenv("OLLAMA_MODEL", "llama3"))
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
