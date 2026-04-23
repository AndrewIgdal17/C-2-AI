import re

from openai import AsyncOpenAI

from app.config import LLM_API_BASE, LLM_API_KEY, LLM_MODEL

client = AsyncOpenAI(base_url=LLM_API_BASE, api_key=LLM_API_KEY)

_THINK_RE = re.compile(r"<think>[\s\S]*?</think>", re.IGNORECASE)


async def chat(messages: list[dict], temperature: float = 0.0) -> str:
    try:
        response = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=2048,
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )
    except Exception:
        response = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=2048,
        )
    text = response.choices[0].message.content or ""
    cleaned = _THINK_RE.sub("", text).strip()
    if cleaned:
        return cleaned
    match = re.search(r"<think>([\s\S]*)</think>", text, re.IGNORECASE)
    if match:
        inner = match.group(1).strip()
        sql_match = re.search(r"(SELECT\b[\s\S]+?)(?:```|$)", inner, re.IGNORECASE)
        if sql_match:
            return sql_match.group(1).strip()
        return inner
    return text.strip()
