from __future__ import annotations

import time
from typing import Any, Dict, List

try:
    from .base import BaseProvider
except ImportError:
    from providers.base import BaseProvider


KEYWORDS = {
    "meeting": ["会议", "开会", "会议室", "PPT", "议程"],
    "shopping": ["买", "购买", "购物", "订单", "价格"],
    "trip": ["机场", "车票", "机票", "出差", "旅行"],
    "pickup": ["接", "接人", "校门", "车站"],
}

DEFAULT_OMISSIONS = {
    "meeting": ["attendees", "room", "agenda", "materials"],
    "shopping": ["quantity", "budget"],
    "trip": ["tickets", "weather"],
    "pickup": ["person_name", "time_window"],
}


class DummyProvider(BaseProvider):
    async def predict(self, text: str) -> Dict[str, Any]:
        start = time.time()
        text = text or ""
        best_label = "meeting"
        best_score = 0.5
        for label, kws in KEYWORDS.items():
            score = sum(1 for k in kws if k in text)
            if score > best_score:
                best_score = float(min(1.0, 0.5 + score * 0.1))
                best_label = label
        omissions: List[str] = DEFAULT_OMISSIONS.get(best_label, [])
        latency_ms = int((time.time() - start) * 1000)
        return {
            "task_type": best_label,
            "confidence": best_score,
            "potential_omissions": omissions,
            "latency_ms": latency_ms,
            "model_version": "dummy:v1",
        } 