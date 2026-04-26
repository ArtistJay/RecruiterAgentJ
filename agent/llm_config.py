"""Central LLM configuration — routes each agent to the right model.

Supports Groq (free tier), OpenAI (paid), and Local (Ollama) providers.
Models are mapped by INTELLIGENCE LEVEL to preserve quality across providers:

    Groq Free Tier          →    OpenAI Equivalent
    ─────────────────────────────────────────────────
    Llama 3.1-8B (parse)    →    GPT-4.1-nano     (simple extraction)
    Llama 4 Scout 17B       →    GPT-4.1-mini     (technical reasoning)
    Llama 3.3-70B (convo)   →    GPT-4.1          (natural conversation)
    Qwen3-32B (scoring)     →    GPT-4.1-mini     (structured analysis)
    Llama 3.1-8B (ranking)  →    GPT-4.1-nano     (simple ranking)
"""

import os
from dotenv import load_dotenv

load_dotenv()


def get_llm(agent_name: str):
    """
    Routes agents to specific models based on task complexity.
    Provider chosen via LLM_PROVIDER env var: "groq" | "openai" | "local"
    """
    provider = os.getenv("LLM_PROVIDER", "groq").lower()
    mode = os.getenv("MODE", "cloud")

    # === LOCAL MODE (Ollama) ===
    if mode == "local" or provider == "local":
        from langchain_ollama import ChatOllama
        return ChatOllama(model=os.getenv("LOCAL_MODEL", "llama3.1:8b"))

    # === OPENAI MODE ===
    if provider == "openai":
        from langchain_openai import ChatOpenAI

        openai_model_map = {
            "inparse": os.getenv("OPENAI_INPARSE_MODEL", "gpt-4.1-nano"),
            "scout":   os.getenv("OPENAI_SCOUT_MODEL",   "gpt-4.1-mini"),
            "convo":   os.getenv("OPENAI_CONVO_MODEL",    "gpt-4.1"),
            "scoring": os.getenv("OPENAI_SCORING_MODEL",  "gpt-4.1-mini"),
            "ranking": os.getenv("OPENAI_RANKING_MODEL",  "gpt-4.1-nano"),
        }

        selected = openai_model_map.get(agent_name, "gpt-4.1-nano")

        return ChatOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            model=selected,
            temperature=0.1,
        )

    # === GROQ MODE (default, free tier) ===
    from langchain_groq import ChatGroq

    groq_model_map = {
        "inparse": os.getenv("INPARSE_MODEL", "llama-3.1-8b-instant"),
        "scout":   os.getenv("SCOUT_MODEL",   "meta-llama/llama-4-scout-17b-16e-instruct"),
        "convo":   os.getenv("CONVO_MODEL",    "llama-3.3-70b-versatile"),
        "scoring": os.getenv("SCORING_MODEL",  "qwen/qwen3-32b"),
        "ranking": os.getenv("RANKING_MODEL",  "llama-3.1-8b-instant"),
    }

    selected = groq_model_map.get(agent_name, "llama-3.1-8b-instant")

    return ChatGroq(
        api_key=os.getenv("GROQ_API_KEY"),
        model_name=selected,
        temperature=0.1,
    )
