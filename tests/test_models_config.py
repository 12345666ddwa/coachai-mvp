#!/usr/bin/env python3
"""CoachAI — model-provider configuration tests (no network / no API calls).

Verifies the provider registry in agents/models.py, especially the local
Ollama branch (no API key needed; placeholder key injected by _get_client).

Run:  python3 tests/test_models_config.py
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import agents.models as m  # noqa: E402

FAILURES = 0


def check(name, cond):
    global FAILURES
    status = "PASS" if cond else "FAIL"
    if not cond:
        FAILURES += 1
    print(f"{status}: {name}")


def test_ollama_registered():
    check("ollama in PROVIDER_ENV_KEY", "ollama" in m.PROVIDER_ENV_KEY)
    check("ollama in PROVIDER_DEFAULT_BASE_URL", "ollama" in m.PROVIDER_DEFAULT_BASE_URL)
    check("ollama in PROVIDER_DEFAULT_MODEL", "ollama" in m.PROVIDER_DEFAULT_MODEL)


def test_ollama_defaults():
    check("ollama base url default",
          m.PROVIDER_DEFAULT_BASE_URL["ollama"] == os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1"))
    check("ollama model default",
          m.PROVIDER_DEFAULT_MODEL["ollama"] == os.getenv("OLLAMA_MODEL", "qwen2.5:7b"))


def test_ollama_client_no_key():
    # Must NOT raise even when OLLAMA_API_KEY is unset (local server needs none).
    saved = os.environ.pop("OLLAMA_API_KEY", None)
    m._client_cache.pop("ollama", None)
    try:
        client = m._get_client("ollama")
        check("ollama client builds without key", client is not None)
        check("ollama placeholder key used",
              client.api_key == "ollama")
    finally:
        if saved is not None:
            os.environ["OLLAMA_API_KEY"] = saved


def test_default_model_for():
    check("_default_model_for(ollama)", m._default_model_for("ollama") == m.PROVIDER_DEFAULT_MODEL["ollama"])
    check("_default_model_for(deepseek)", m._default_model_for("deepseek") == m.PROVIDER_DEFAULT_MODEL["deepseek"])
    check("_default_model_for(unknown) falls back", m._default_model_for("nope") == m.DEFAULT_MODEL)


def test_unsupported_provider_raises():
    try:
        m.complete("s", "u", provider="does-not-exist")
        check("unsupported provider raises", False)
    except RuntimeError as e:
        check("unsupported provider raises", "Unsupported provider" in str(e))


if __name__ == "__main__":
    test_ollama_registered()
    test_ollama_defaults()
    test_ollama_client_no_key()
    test_default_model_for()
    test_unsupported_provider_raises()
    print()
    if FAILURES:
        print(f"{FAILURES} FAILED")
        sys.exit(1)
    print("all model-config tests passed")
