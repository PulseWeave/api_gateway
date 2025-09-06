from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

try:
    from .base import BaseProvider
    from ..prompt_templates import TASK_TYPES, FORGET_RULES, SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
except ImportError:
    from providers.base import BaseProvider
    from prompt_templates import TASK_TYPES, FORGET_RULES, SYSTEM_PROMPT, USER_PROMPT_TEMPLATE


class DeepSeekProvider(BaseProvider):
    """DeepSeek-V3提供商，支持两种模式：
    - sdk: 使用官方Python SDK（需安装 deepseek 包）
    - http: 使用HTTP REST API
    通过config.provider.mode选择：sdk | http
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.mode = (config.get("mode") or "sdk").lower()
        self.base_url = config.get("base_url", "https://api.deepseek.com")
        self.model = config.get("model", "deepseek-chat")  # DeepSeek-V3 对话模型名示例
        self.timeout = int(config.get("timeout_sec", 8))
        self.max_tokens = int(config.get("max_tokens", 300))
        self.temperature = float(config.get("temperature", 0.0))
        self.top_p = float(config.get("top_p", 1.0))
        self.api_key = os.getenv("DEEPSEEK_API_KEY", "") or config.get("api_key", "")
        if not self.api_key:
            raise RuntimeError("DEEPSEEK_API_KEY 未设置")
        self._client = None
        if self.mode == "sdk":
            try:
                from deepseek import DeepSeek  # type: ignore
                self._client = DeepSeek(api_key=self.api_key)
            except Exception as e:  # pragma: no cover
                raise RuntimeError("未安装或无法导入 deepseek SDK，请改用http模式或安装SDK：pip install deepseek") from e

    @retry(wait=wait_exponential(multiplier=0.5, min=0.5, max=4), stop=stop_after_attempt(1 + int(os.getenv("DEEPSEEK_RETRIES", "2"))))
    async def predict(self, text: str = None, event_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行推理 - 支持文本或事件数据"""
        start = time.time()

        # 确定要分析的文本
        text_to_analyze = text
        if not text_to_analyze and event_data:
            text_to_analyze = event_data.get("transcript")

        if not text_to_analyze:
            raise ValueError("必须提供文本或事件中的transcript字段")

        if self.mode == "sdk":
            result = await self._predict_via_sdk(text_to_analyze, event_data)
        else:
            result = await self._predict_via_http(text_to_analyze, event_data)
        result["latency_ms"] = result.get("latency_ms", int((time.time() - start) * 1000))
        # 回退补全 summary_text/suggested_plan
        task_type = result.get("task_type", "unknown")
        confidence = float(result.get("confidence", 0.5))
        omissions = result.get("potential_omissions", []) or []
        if not result.get("summary_text"):
            task_descriptions = {
                "trip": "出行安排",
                "meeting": "会议安排",
                "shopping": "购物计划",
                "work": "工作任务",
                "health": "健康相关事务",
                "entertainment": "娱乐活动",
                "learning": "学习计划",
                "social": "社交活动",
                "finance": "财务事务",
                "other": "日常事务"
            }

            task_desc = task_descriptions.get(task_type, "日常事务")
            confidence_desc = "很确定" if confidence > 0.8 else "比较确定" if confidence > 0.6 else "初步判断"

            if omissions:
                omissions_txt = "、".join(omissions[:2])  # 只显示前2个
                result["summary_text"] = f"{confidence_desc}这是一个{task_desc}，不过可能还需要考虑{omissions_txt}等细节"
            else:
                result["summary_text"] = f"{confidence_desc}这是一个{task_desc}，信息相对比较完整"
        if not result.get("suggested_plan"):
            if task_type == "trip":
                result["suggested_plan"] = "建议提前一晚准备好证件和行李，设置多个闹钟确保不会睡过头，可以提前预约出租车或安排家人送行，记得查看天气准备合适的衣物，充电宝和数据线也别忘了带上"
            elif task_type == "meeting":
                result["suggested_plan"] = "提前确认会议室位置和参会人员，准备好相关材料和议程，建议提前10-15分钟到场熟悉环境，如果是重要会议可以提前演练一下要讲的内容"
            elif task_type == "shopping":
                result["suggested_plan"] = "先列个详细的购物清单避免遗漏，可以提前比较一下价格和优惠信息，设定一个合理的预算范围，选择人少的时间段去购物会更舒适"
            elif task_type == "work":
                result["suggested_plan"] = "先把任务分解成几个小步骤，设定合理的时间节点，准备好需要的工具和资料，如果遇到困难及时寻求帮助，记得劳逸结合"
            elif task_type == "health":
                result["suggested_plan"] = "记录下具体的症状和时间，选择合适的医院科室，提前预约挂号避免排队，带上身份证和以往的检查资料，如果不舒服建议有人陪同"
            elif task_type == "social":
                result["suggested_plan"] = "提前确认时间地点，考虑一下参与人员的喜好安排活动内容，准备一些话题避免冷场，注意天气情况准备合适的着装"
            else:
                result["suggested_plan"] = "建议先明确具体的目标和要求，制定一个可行的时间计划，准备好必要的资源和工具，遇到问题及时调整方案"
        return result

    async def _predict_via_http(self, text: str, event_data: Dict[str, Any] = None) -> Dict[str, Any]:
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
        url = f"{self.base_url}/v1/chat/completions"

        # 增加超时时间，使用更详细的超时配置
        timeout_config = httpx.Timeout(
            connect=10.0,  # 连接超时
            read=30.0,     # 读取超时
            write=10.0,    # 写入超时
            pool=10.0      # 连接池超时
        )

        try:
            async with httpx.AsyncClient(timeout=timeout_config) as client:
                resp = await client.post(url, headers=headers, json=payload)

                # 添加详细的错误信息
                if resp.status_code != 200:
                    error_text = resp.text
                    raise ValueError(f"DeepSeek API错误 {resp.status_code}: {error_text}")

                data = resp.json()

        except httpx.ReadTimeout:
            raise ValueError("DeepSeek API读取超时，请检查网络连接或稍后重试。建议增加timeout_sec配置")
        except httpx.ConnectTimeout:
            raise ValueError("DeepSeek API连接超时，请检查网络连接和防火墙设置")
        except httpx.TimeoutException:
            raise ValueError("DeepSeek API请求超时，请检查网络连接")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise ValueError("API密钥无效，请检查config.yaml中的api_key设置")
            elif e.response.status_code == 429:
                raise ValueError("请求频率过高或账户余额不足，请稍后重试")
            elif e.response.status_code == 403:
                raise ValueError("API密钥没有权限，请检查密钥是否正确")
            else:
                raise ValueError(f"DeepSeek API错误 {e.response.status_code}: {e.response.text}")
        except Exception as e:
            raise ValueError(f"DeepSeek API请求失败: {str(e)}")

        # 检查响应格式
        if "choices" not in data or not data["choices"]:
            raise ValueError(f"DeepSeek API响应格式错误: {data}")

        content = data["choices"][0]["message"]["content"].strip()

        try:
            parsed = json.loads(content)
        except Exception as e:
            raise ValueError(f"上游返回非JSON: {content[:200]}. 解析错误: {str(e)}")
        return {
            "task_type": parsed.get("task_type", "unknown"),
            "confidence": float(parsed.get("confidence", 0.5)),
            "potential_omissions": parsed.get("potential_omissions", []),
            "summary_text": parsed.get("summary_text", ""),
            "suggested_plan": parsed.get("suggested_plan", ""),
            "model_version": f"deepseek:{self.model}",
        }

    async def _predict_via_sdk(self, text: str, event_data: Dict[str, Any] = None) -> Dict[str, Any]:
        # SDK 同步/异步接口以官方为准；这里用同步包装异步的简单示例
        from anyio.to_thread import run_sync

        def _call_sync() -> Dict[str, Any]:
            system_msg = {"role": "system", "content": SYSTEM_PROMPT}
            user_prompt = USER_PROMPT_TEMPLATE.format(
                task_types=", ".join(TASK_TYPES),
                forget_rules=json.dumps(FORGET_RULES, ensure_ascii=False),
                input_text=text,
            )
            user_msg = {"role": "user", "content": user_prompt}
            messages = [system_msg, user_msg]
            # 伪代码：以SDK文档为准
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                top_p=self.top_p,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"},
                timeout=self.timeout,
            )
            content = resp.choices[0].message.content.strip()
            parsed = json.loads(content)
            return {
                "task_type": parsed.get("task_type", "unknown"),
                "confidence": float(parsed.get("confidence", 0.5)),
                "potential_omissions": parsed.get("potential_omissions", []),
                "summary_text": parsed.get("summary_text", ""),
                "suggested_plan": parsed.get("suggested_plan", ""),
                "model_version": f"deepseek:{self.model}",
            }

        return await run_sync(_call_sync) 