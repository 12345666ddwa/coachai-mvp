"""
CoachAI — Model Abstraction Layer
=================================

Design principles (project-wide conventions):
    * Every agent / graph must call LLMs only through the functions in this
      module. Directly `import openai` (or any other SDK) in other modules is
      forbidden.
    * When adding Gemini / Ollama / Claude in the future, simply add one more
      provider branch inside `complete()` (and read the corresponding
      base_url / model / key in _resolve_config); upstream code needs zero
      changes.

Currently supported:
    - deepseek : OpenAI-compatible protocol -> https://api.deepseek.com/v1
    - Configuration sources: project-root .env (DEEPSEEK_API_KEY /
      DEEPSEEK_BASE_URL) and the DEFAULT_MODEL constant at the top of this file.

Typical usage:
    reply = complete("You are a strict HSC marker.",
                     "Mark this essay: ...", temperature=0.2)
"""

import os

from openai import OpenAI
from dotenv import load_dotenv

# .env under the project root (ai-coach/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# ---------------------------------------------------------------- providers
# Each provider needs: env-var key name + default base_url + default model
PROVIDER_ENV_KEY = {
    "deepseek": "DEEPSEEK_API_KEY",
    # "gemini": "GEMINI_API_KEY",   # future: add one line + one branch below
    # "ollama": "OLLAMA_API_KEY",   # future: base_url points to local 11434/v1
}

PROVIDER_DEFAULT_BASE_URL = {
    "deepseek": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
    # "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
    # "ollama": "http://127.0.0.1:11434/v1",
}

DEFAULT_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")

_client_cache: dict = {}


def _get_client(provider: str = "deepseek") -> OpenAI:
    """Return a (cached) OpenAI-compatible client for the given provider."""
    if provider not in _client_cache:
        key = os.getenv(PROVIDER_ENV_KEY[provider], "")
        if not key:
            raise RuntimeError(
                f"[models.py] Missing {PROVIDER_ENV_KEY[provider]}; "
                f"please check that {BASE_DIR}/.env is configured."
            )
        _client_cache[provider] = OpenAI(
            api_key=key,
            base_url=PROVIDER_DEFAULT_BASE_URL[provider],
            timeout=60,
            max_retries=2,
        )
    return _client_cache[provider]


def complete(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.3,
    model: str | None = None,
    provider: str = "deepseek",
    max_tokens: int = 4096,
) -> str:
    """
    Unified model-call entry point.

    Args:
        system_prompt: System prompt (role / marking criteria, etc.).
        user_prompt:   User / student content.
        temperature:   Sampling temperature; 0~0.3 is recommended for marking
                       tasks to keep results consistent.
        model:         Override the default model name; None uses DEFAULT_MODEL.
        provider:      'deepseek' (extensible to 'gemini' / 'ollama' later).
        max_tokens:    Output cap.

    Returns:
        The model's reply text (stripped).

    Raises:
        RuntimeError: on unsupported provider, missing API key, or call
                      failure.
    """
    if provider not in PROVIDER_ENV_KEY:
        raise RuntimeError(f"[models.py] Unsupported provider: {provider}")

    client = _get_client(provider)
    resp = client.chat.completions.create(
        model=model or DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    try:
        text = resp.choices[0].message.content
    except (IndexError, AttributeError) as exc:  # pragma: no cover
        raise RuntimeError(
            f"[models.py] Unexpected response format: {exc} | {resp}"
        ) from exc
    if not text:
        raise RuntimeError("[models.py] Model returned empty content (finish_reason="
                           f"{resp.choices[0].finish_reason})")
    return text.strip()
