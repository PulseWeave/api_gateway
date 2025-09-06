from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, model_validator


# 事件数据结构定义
class EventType(BaseModel):
    label: str = Field(..., description="事件类型标签")
    ontology_id: Optional[str] = Field(default=None, description="本体ID")


class Speaker(BaseModel):
    speaker_id: str = Field(..., description="说话人ID")
    speaker_label: str = Field(..., description="说话人标签")
    is_user: bool = Field(..., description="是否为用户")
    speaker_confidence: float = Field(..., description="说话人识别置信度")


class AudioFeatures(BaseModel):
    avg_volume_db: Optional[float] = Field(default=None, description="平均音量")
    snr_db: Optional[float] = Field(default=None, description="信噪比")
    speech_rate_wpm: Optional[float] = Field(default=None, description="语速")
    language: Optional[str] = Field(default=None, description="语言")
    asr_confidence: Optional[float] = Field(default=None, description="ASR置信度")


class Intent(BaseModel):
    intent_name: str = Field(..., description="意图名称")
    score: float = Field(..., description="意图得分")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="意图参数")


class NLU(BaseModel):
    intents: List[Intent] = Field(default_factory=list, description="意图列表")
    summary: Optional[str] = Field(default=None, description="摘要")


class Entity(BaseModel):
    type: str = Field(..., description="实体类型")
    value: str = Field(..., description="实体值")
    confidence: float = Field(..., description="实体置信度")


class Emotion(BaseModel):
    primary: Optional[str] = Field(default=None, description="主要情绪")
    scores: Dict[str, float] = Field(default_factory=dict, description="情绪得分")


class Privacy(BaseModel):
    contains_pii: bool = Field(default=False, description="是否包含PII")
    pii_types: List[str] = Field(default_factory=list, description="PII类型")
    redaction_suggested: bool = Field(default=False, description="是否建议脱敏")


class RecordingReference(BaseModel):
    recording_id: Optional[str] = Field(default=None, description="录音ID")
    audio_segment_id: Optional[str] = Field(default=None, description="音频片段ID")
    audio_url: Optional[str] = Field(default=None, description="音频URL")


class Raw(BaseModel):
    rttm_segment: Optional[str] = Field(default=None, description="RTTM片段")
    original_annotation: Optional[str] = Field(default=None, description="原始标注")


class EventData(BaseModel):
    event_id: str = Field(..., description="事件唯一ID")
    event_type: EventType = Field(..., description="事件类型")
    recording_reference: Optional[RecordingReference] = Field(default=None, description="录音引用")
    start_time: str = Field(..., description="开始时间")
    end_time: str = Field(..., description="结束时间")
    start_offset_sec: float = Field(..., description="开始偏移秒数")
    end_offset_sec: float = Field(..., description="结束偏移秒数")
    confidence: float = Field(..., description="置信度")
    speakers: List[Speaker] = Field(default_factory=list, description="说话人列表")
    transcript: Optional[str] = Field(default=None, description="转写文本")
    audio_features: Optional[AudioFeatures] = Field(default=None, description="音频特征")
    nlu: Optional[NLU] = Field(default=None, description="NLU结果")
    entities: List[Entity] = Field(default_factory=list, description="实体列表")
    emotion: Optional[Emotion] = Field(default=None, description="情绪")
    privacy: Optional[Privacy] = Field(default=None, description="隐私信息")
    raw: Optional[Raw] = Field(default=None, description="原始数据")
    tags: List[str] = Field(default_factory=list, description="标签")
    related_event_ids: List[str] = Field(default_factory=list, description="关联事件ID")


class InferRequest(BaseModel):
    text: Optional[str] = Field(default=None, description="要推理的文本内容（简单模式）")
    event: Optional[EventData] = Field(default=None, description="完整的事件数据（高级模式）")

    @model_validator(mode="before")
    @classmethod
    def validate_input(cls, values):
        if isinstance(values, dict):
            text = values.get("text")
            event = values.get("event")

            # 必须提供text或event中的transcript
            if not text and not (event and event.get("transcript")):
                raise ValueError("必须提供 text 字段或 event.transcript 字段")
        return values


class InferResponse(BaseModel):
    # 基础推理结果
    task_type: str = Field(..., description="任务类型（从定义列表中取值）")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度（0~1）")
    potential_omissions: List[str] = Field(default_factory=list, description="可能遗漏项")
    latency_ms: int = Field(..., ge=0, description="推理耗时（毫秒）")
    model_version: str = Field(..., description="模型版本")
    summary_text: str = Field(default="", description="智能摘要")
    suggested_plan: str = Field(default="", description="行动建议")

    # 增强的智能分析结果
    enhanced_nlu: Optional[NLU] = Field(default=None, description="增强的NLU结果")
    extracted_entities: List[Entity] = Field(default_factory=list, description="提取的实体")
    suggested_tags: List[str] = Field(default_factory=list, description="建议的标签")
    priority_level: Optional[str] = Field(default=None, description="优先级等级：high/medium/low")
    reminder_suggestions: List[str] = Field(default_factory=list, description="提醒建议")

    # 事件相关信息（如果输入包含事件数据）
    event_analysis: Optional[Dict[str, Any]] = Field(default=None, description="事件分析结果")
    speaker_insights: Optional[Dict[str, Any]] = Field(default=None, description="说话人洞察")
    audio_quality_assessment: Optional[Dict[str, Any]] = Field(default=None, description="音频质量评估")


class HealthResponse(BaseModel):
    status: str = "ok"
