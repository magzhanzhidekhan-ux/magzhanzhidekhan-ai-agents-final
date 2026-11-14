"""Single place that talks to the LLM. Everything else uses these functions."""
import os

from dotenv import load_dotenv

load_dotenv()


class LLMError(Exception):
    """Configuration problem or a failed model call, with a readable message."""


def build_model():
    key, name = os.getenv("OPENAI_API_KEY"), os.getenv("MODEL_NAME")
    if not key:
        raise LLMError("OPENAI_API_KEY is not set. Copy .env.example to .env and fill it in.")
    if not name:
        raise LLMError("MODEL_NAME is not set (I use gpt-5.6-luna).")
    from langchain_openai import ChatOpenAI
    # reasoning is off: this model rejects function tools while reasoning is on (needed from week 13)
    return ChatOpenAI(model=name, reasoning_effort=os.getenv("REASONING_EFFORT", "none"),
                      timeout=60, max_retries=2)


def ask(model, system: str, user: str) -> str:
    """One plain request. Returns text or raises LLMError."""
    if not user or not user.strip():
        raise LLMError("Empty request.")
    try:
        reply = model.invoke([("system", system), ("user", user)])
    except Exception as e:                       # network, auth, rate limit, bad request
        raise LLMError(f"Model call failed: {type(e).__name__}: {str(e)[:200]}") from e
    text = reply.content if isinstance(reply.content, str) else str(reply.content)
    if not text.strip():
        raise LLMError("The model returned an empty answer.")
    return text.strip()