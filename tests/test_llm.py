"""CoachAI LLM connectivity test — real call to DeepSeek.

Run:      python tests/test_llm.py      (or pytest tests/)
Requires: DEEPSEEK_API_KEY configured in ai-coach/.env
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.models import complete  # noqa: E402


def test_deepseek_connectivity() -> None:
    reply = complete(
        system_prompt="You are a helpful assistant. Be terse.",
        user_prompt="Reply with exactly: PONG",
        temperature=0.0,
    )
    assert reply, "Empty reply — the model returned no content"
    assert "PONG" in reply.upper(), f"PONG not found in reply; actual reply: {reply!r}"
    print(f"[PASS] Model reply: {reply!r} (len={len(reply)})")


if __name__ == "__main__":
    test_deepseek_connectivity()
    print("[OK] DeepSeek connectivity test passed")
