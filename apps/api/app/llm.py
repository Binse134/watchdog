import httpx

from app.config import settings


class LlmError(Exception):
    """The configured LLM provider is unreachable or returned an error."""


def generate_text(prompt: str) -> str:
    """Generates text from the configured LLM provider.

    Currently calls Ollama directly over HTTP (no SDK, same approach as
    N8nClient/email.py). Kept behind this one function so swapping providers
    later (e.g. a hosted API once this deploys to a VPS without the Mac's
    GPU) only means changing this file, not its callers.
    """
    try:
        response = httpx.post(
            f"{settings.ollama_base_url}/api/generate",
            json={"model": settings.ollama_model, "prompt": prompt, "stream": False},
            timeout=180.0,
        )
    except httpx.RequestError as exc:
        raise LlmError(f"Could not reach Ollama at {settings.ollama_base_url}: {exc}") from exc

    if response.status_code >= 400:
        raise LlmError(f"Ollama returned {response.status_code}: {response.text[:300]}")

    return response.json()["response"].strip()
