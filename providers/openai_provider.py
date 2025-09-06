from __future__ import annotations

import json
import os
import time
from typing import Any, Dict

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

try:
    from .base import BaseProvider
    from ..prompt_templates import TASK_TYPES, FORGET_RULES, SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
except ImportError:
    from providers.base import BaseProvider
    from prompt_templates import TASK_TYPES, FORGET_RULES, SYSTEM_PROMPT, USER_PROMPT_TEMPLATE


class OpenAIProvider(BaseProvider):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get("base_url", "https://api.openai.com/v1")
        self.model = config.get("model", "gpt-4o-mini")
        self.timeout = int(config.get("timeout_sec", 8))
        self.max_tokens = int(config.get("max_tokens", 300))
        self.temperature = float(config.get("temperature", 0.0))
        self.top_p = float(config.get("top_p", 1.0))
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY 未设置")

    @retry(wait=wait_exponential(multiplier=0.5, min=0.5, max=4), stop=stop_after_attempt(1 + int(os.getenv("OPENAI_RETRIES", "2"))))
    async def predict(self, text: str) -> Dict[str, Any]:
        start = time.time()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        system_msg = {"role": "system", "content": SYSTEM_PROMPT}
        user_prompt = USER_PROMPT_TEMPLATE.format(
            task_types=", ".join(TASK_TYPES),
            forget_rules=json.dumps(FORGET_RULES, ensure_ascii=False),
            input_text=text,
        )
        user_msg = {"role": "user", "content": user_prompt}
        payload = {
            "model": self.model,
            "messages": [system_msg, user_msg],
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"},
        }
        url = f"{self.base_url}/chat/completions"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        content = data["choices"][0]["message"]["content"].strip()
        try:
            parsed = json.loads(content)
        except Exception:
            raise ValueError(f"上游返回非JSON: {content[:200]}")
        latency_ms = int((time.time() - start) * 1000)
        return {
            "task_type": parsed.get("task_type", "unknown"),
            "confidence": float(parsed.get("confidence", 0.5)),
            "potential_omissions": parsed.get("potential_omissions", []),
            "latency_ms": latency_ms,
            "model_version": f"openai:{self.model}",
        } 