"""CoachAI LLM 连通性测试 — 真实调用 DeepSeek。

运行:  python tests/test_llm.py      (或 pytest tests/)
要求:  ai-coach/.env 中已配置 DEEPSEEK_API_KEY
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
    assert reply, "回复为空 — 模型未返回内容"
    assert "PONG" in reply.upper(), f"回复中未找到 PONG，实际回复: {reply!r}"
    print(f"[PASS] 模型回复: {reply!r} (len={len(reply)})")


if __name__ == "__main__":
    test_deepseek_connectivity()
    print("[OK] DeepSeek 连通测试通过")
