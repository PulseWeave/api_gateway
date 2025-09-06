import os
import time
import json
import uuid
from typing import Any, Dict

import yaml
from fastapi import FastAPI, Depends, HTTPException, Header, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

try:
    # 尝试相对导入（作为包运行时）
    from .schemas import InferRequest, InferResponse, HealthResponse
    from .providers import get_provider
    from .websocket_manager import websocket_manager, handle_websocket_message
    from .task_processor import start_task_processor, stop_task_processor
except ImportError:
    # 绝对导入（直接运行时）
    from schemas import InferRequest, InferResponse, HealthResponse
    from providers import get_provider
    from websocket_manager import websocket_manager, handle_websocket_message
    from task_processor import start_task_processor, stop_task_processor

load_dotenv()

app = FastAPI(title="PulseWeave API Gateway", version="0.1.0")

# 启动和关闭事件
@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化"""
    # 启动任务处理器
    await start_task_processor(PROVIDER, max_workers=3)

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的清理"""
    # 停止任务处理器
    await stop_task_processor()

# CORS（前端本地页面或内置UI使用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"]
    ,
    allow_headers=["*"]
)

# 内置简易UI（/ui）
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(STATIC_DIR):
    app.mount("/ui", StaticFiles(directory=STATIC_DIR, html=True), name="ui")



def load_config() -> Dict[str, Any]:
    config_path = os.getenv("API_CONFIG", os.path.join(os.path.dirname(__file__), "config.yaml"))
    if not os.path.exists(config_path):
        # 允许只用example启动：当config.yaml不存在时，退回example
        example_path = os.path.join(os.path.dirname(__file__), "config.example.yaml")
        config_path = example_path
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


CONFIG = load_config()
ProviderClass = get_provider(CONFIG.get("provider", {}).get("name", "dummy"))
PROVIDER = ProviderClass(CONFIG.get("provider", {}))

REQUIRE_AUTH = bool(CONFIG.get("service", {}).get("require_auth", True))
GATEWAY_KEY = os.getenv("GATEWAY_API_KEY", "")


async def check_auth(authorization: str | None = Header(default=None)) -> None:
    if not REQUIRE_AUTH:
        return
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="缺少或非法的Authorization头")
    token = authorization.split(" ", 1)[1].strip()
    if not GATEWAY_KEY or token != GATEWAY_KEY:
        raise HTTPException(status_code=401, detail="鉴权失败")


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    # 有内置UI则跳转到 /ui，否则跳转到 /health
    if os.path.isdir(STATIC_DIR):
        return RedirectResponse(url="/ui/")
    return RedirectResponse(url="/health")


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket连接端点"""
    # 生成客户端ID
    client_id = str(uuid.uuid4())

    try:
        # 建立连接
        await websocket_manager.connect(websocket, client_id)

        while True:
            # 接收消息
            data = await websocket.receive_text()

            try:
                message = json.loads(data)

                # 处理消息
                response = await handle_websocket_message(client_id, message)

                # 发送响应
                if response:
                    await websocket_manager.send_to_client(client_id, response)

            except json.JSONDecodeError:
                await websocket_manager.send_to_client(client_id, {
                    "type": "error",
                    "message": "无效的JSON格式"
                })
            except Exception as e:
                await websocket_manager.send_to_client(client_id, {
                    "type": "error",
                    "message": f"处理消息时发生错误: {str(e)}"
                })

    except WebSocketDisconnect:
        await websocket_manager.disconnect(client_id)
    except Exception as e:
        print(f"WebSocket连接异常: {e}")
        await websocket_manager.disconnect(client_id)


@app.get("/ws/stats")
async def get_websocket_stats():
    """获取WebSocket统计信息"""
    return await websocket_manager.get_stats()


@app.post("/infer", response_model=InferResponse)
async def infer(request: InferRequest, _: None = Depends(check_auth)) -> InferResponse:
    """智能推理接口 - 支持文本或完整事件数据"""

    # 提取要分析的文本
    input_text = None
    event_data = None

    if request.text:
        input_text = request.text.strip()
    elif request.event and request.event.transcript:
        input_text = request.event.transcript.strip()
        event_data = request.event.dict()

    if not input_text:
        raise HTTPException(status_code=422, detail="必须提供 text 字段或 event.transcript 字段")

    start = time.time()
    try:
        # 调用推理服务，传递事件数据（如果有）
        result = await PROVIDER.predict(input_text, event_data)

        # 如果有事件数据，进行额外的分析
        if event_data:
            result = await _enhance_with_event_analysis(result, event_data)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"上游调用失败: {e}")

    # 统一补充延迟
    if "latency_ms" not in result:
        result["latency_ms"] = int((time.time() - start) * 1000)

    try:
        return InferResponse(**result)
    except Exception as e:
        # 防御：如果供应商返回字段不完整
        raise HTTPException(status_code=502, detail=f"响应解析失败: {e}")


async def _enhance_with_event_analysis(result: Dict[str, Any], event_data: Dict[str, Any]) -> Dict[str, Any]:
    """基于事件数据增强分析结果"""

    # 提取实体
    extracted_entities = []
    if event_data.get("entities"):
        for entity in event_data["entities"]:
            extracted_entities.append({
                "type": entity.get("type", "unknown"),
                "value": entity.get("value", ""),
                "confidence": entity.get("confidence", 0.0)
            })

    # 建议标签
    suggested_tags = []
    if event_data.get("tags"):
        suggested_tags.extend(event_data["tags"])

    # 基于任务类型添加标签
    task_type = result.get("task_type", "other")
    if task_type not in suggested_tags:
        suggested_tags.append(task_type)

    # 优先级评估
    priority_level = "medium"  # 默认中等优先级
    confidence = result.get("confidence", 0.0)
    if confidence > 0.8:
        priority_level = "high"
    elif confidence < 0.4:
        priority_level = "low"

    # 提醒建议
    reminder_suggestions = []
    omissions = result.get("potential_omissions", [])
    for omission in omissions:
        reminder_suggestions.append(f"记得确认{omission}")

    # 事件分析
    event_analysis = {
        "has_speakers": len(event_data.get("speakers", [])) > 0,
        "speaker_count": len(event_data.get("speakers", [])),
        "has_audio_features": event_data.get("audio_features") is not None,
        "contains_pii": event_data.get("privacy", {}).get("contains_pii", False),
        "event_duration_sec": event_data.get("end_offset_sec", 0) - event_data.get("start_offset_sec", 0)
    }

    # 说话人洞察
    speaker_insights = None
    speakers = event_data.get("speakers", [])
    if speakers:
        user_speakers = [s for s in speakers if s.get("is_user", False)]
        speaker_insights = {
            "total_speakers": len(speakers),
            "user_speakers": len(user_speakers),
            "multi_speaker": len(speakers) > 1,
            "primary_speaker": speakers[0].get("speaker_label", "unknown") if speakers else None
        }

    # 音频质量评估
    audio_quality_assessment = None
    audio_features = event_data.get("audio_features")
    if audio_features:
        asr_confidence = audio_features.get("asr_confidence")
        snr_db = audio_features.get("snr_db")

        quality = "good"
        if asr_confidence and asr_confidence < 0.7:
            quality = "poor"
        elif snr_db and snr_db < 10:
            quality = "poor"
        elif asr_confidence and asr_confidence < 0.85:
            quality = "fair"

        audio_quality_assessment = {
            "overall_quality": quality,
            "asr_confidence": asr_confidence,
            "snr_db": snr_db,
            "language": audio_features.get("language"),
            "speech_rate_wpm": audio_features.get("speech_rate_wpm")
        }

    # 增强NLU结果
    enhanced_nlu = None
    if event_data.get("nlu"):
        enhanced_nlu = {
            "intents": event_data["nlu"].get("intents", []),
            "summary": event_data["nlu"].get("summary") or result.get("summary_text", "")
        }

    # 更新结果
    result.update({
        "extracted_entities": extracted_entities,
        "suggested_tags": suggested_tags,
        "priority_level": priority_level,
        "reminder_suggestions": reminder_suggestions,
        "event_analysis": event_analysis,
        "speaker_insights": speaker_insights,
        "audio_quality_assessment": audio_quality_assessment,
        "enhanced_nlu": enhanced_nlu
    })

    return result


# 简化版本 - 只保留基本推理功能