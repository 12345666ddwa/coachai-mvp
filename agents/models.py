"""
CoachAI — 统一模型接入层 (Model Abstraction Layer)
====================================================

设计原则（项目关键约定）:
    * 所有 agent / graph 只能通过本模块的函数调用大模型，
      禁止在其它模块直接 `import openai` 或使用其它 SDK。
    * 未来接入 Gemini / Ollama / Claude 时，只需在本文件
      `complete()` 内新增一个 provider 分支（并在 _resolve_config
      中读取对应 base_url / model / key），上层代码零改动。

当前支持:
    - deepseek : OpenAI 兼容协议 -> https://api.deepseek.com/v1
    - 配置来源: 项目根目录 .env (DEEPSEEK_API_KEY / DEEPSEEK_BASE_URL)
               以及本文件顶部常量 DEFAULT_MODEL。

典型用法:
    reply = complete("You are a strict HSC marker.",
                     "Mark this essay: ...", temperature=0.2)
"""

import os

from openai import OpenAI
from dotenv import load_dotenv

# 项目根目录 (ai-coach/) 下的 .env
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# ---------------------------------------------------------------- providers
# 每个 provider 需要: 环境变量里的 key 名 + 默认 base_url + 默认 model
PROVIDER_ENV_KEY = {
    "deepseek": "DEEPSEEK_API_KEY",
    # "gemini": "GEMINI_API_KEY",   # 未来: 新增一行 + 下方一个分支
    # "ollama": "OLLAMA_API_KEY",   # 未来: base_url 指向本地 11434/v1
}

PROVIDER_DEFAULT_BASE_URL = {
    "deepseek": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
    # "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
    # "ollama": "http://127.0.0.1:11434/v1",
}

DEFAULT_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")

_client_cache: dict = {}


def _get_client(provider: str = "deepseek") -> OpenAI:
    """按 provider 返回(缓存的) OpenAI 兼容客户端。"""
    if provider not in _client_cache:
        key = os.getenv(PROVIDER_ENV_KEY[provider], "")
        if not key:
            raise RuntimeError(
                f"[models.py] 缺少 {PROVIDER_ENV_KEY[provider]}，"
                f"请检查 {BASE_DIR}/.env 是否已配置。"
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
    统一模型调用入口。

    Args:
        system_prompt: 系统提示词（角色 / 评分标准等）。
        user_prompt:   用户/学生内容。
        temperature:   采样温度，批改任务建议 0~0.3 保证一致性。
        model:         覆盖默认模型名；None 时用 DEFAULT_MODEL。
        provider:      'deepseek'（未来可扩展 'gemini' / 'ollama'）。
        max_tokens:    输出上限。

    Returns:
        模型回复文本（已 strip）。

    Raises:
        RuntimeError: provider 不支持、缺少 API key 或调用失败时。
    """
    if provider not in PROVIDER_ENV_KEY:
        raise RuntimeError(f"[models.py] 不支持的 provider: {provider}")

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
            f"[models.py] 响应格式异常: {exc} | {resp}"
        ) from exc
    if not text:
        raise RuntimeError("[models.py] 模型返回了空内容 (finish_reason="
                           f"{resp.choices[0].finish_reason})")
    return text.strip()
