import re

from openai import AsyncOpenAI

from app.config import LLM_API_BASE, LLM_API_KEY, LLM_MODEL

client = AsyncOpenAI(base_url=LLM_API_BASE, api_key=LLM_API_KEY)

_THINK_RE = re.compile(r"<think>[\s\S]*?</think>", re.IGNORECASE)


async def chat(messages: list[dict], temperature: float = 0.0) -> str:
    response = await client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=4096,
    )
    text = response.choices[0].message.content or ""
    return _THINK_RE.sub("", text).strip()
