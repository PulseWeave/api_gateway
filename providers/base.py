from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseProvider(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    async def predict(self, text: str) -> Dict[str, Any]:
        """返回字段：task_type, confidence, potential_omissions, model_version"""
        raise NotImplementedError 