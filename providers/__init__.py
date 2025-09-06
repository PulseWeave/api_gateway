try:
    # 相对导入
    from .base import BaseProvider
    from .dummy_provider import DummyProvider
    try:
        from .openai_provider import OpenAIProvider  # 可选依赖
    except Exception:  # pragma: no cover
        OpenAIProvider = None  # type: ignore

    try:
        from .deepseek_provider import DeepSeekProvider  # 可选依赖
    except Exception:  # pragma: no cover
        DeepSeekProvider = None  # type: ignore
except ImportError:
    # 绝对导入
    from providers.base import BaseProvider
    from providers.dummy_provider import DummyProvider
    try:
        from providers.openai_provider import OpenAIProvider  # 可选依赖
    except Exception:  # pragma: no cover
        OpenAIProvider = None  # type: ignore

    try:
        from providers.deepseek_provider import DeepSeekProvider  # 可选依赖
    except Exception:  # pragma: no cover
        DeepSeekProvider = None  # type: ignore


def get_provider(name: str):
    name = (name or "").lower()
    if name == "openai" and OpenAIProvider is not None:
        return OpenAIProvider
    if name in ("deepseek", "deepseek-v3") and DeepSeekProvider is not None:
        return DeepSeekProvider
    if name in ("dummy", "mock", "rule"):
        return DummyProvider
    raise ValueError(f"未知的provider: {name}") 