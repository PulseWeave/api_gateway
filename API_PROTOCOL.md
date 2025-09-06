# PulseWeave API 对接协议规范

## 📋 协议概述

**协议名称**: PulseWeave Voice Intelligence API v1.0  
**协议类型**: RESTful HTTP API  
**数据格式**: JSON  
**字符编码**: UTF-8  
**项目定位**: 基于语音的智能备忘和建议工具

---

## 🌐 服务端点

### 基础信息
- **协议**: HTTP/HTTPS
- **方法**: POST
- **Content-Type**: `application/json`
- **字符编码**: UTF-8

### 环境地址
```
开发环境: http://localhost:8000
测试环境: https://test-api.pulseweave.com
生产环境: https://api.pulseweave.com
```

---

## 📡 API接口规范

### 1. 健康检查
```
GET /health
```

**响应**:
```json
{
  "status": "ok"
}
```

### 2. 智能推理接口
```
POST /infer
```

#### 请求格式

**模式A: 简单文本模式（向后兼容）**
```json
{
  "text": "明早七点去机场，记得身份证和充电宝"
}
```

**模式B: 完整事件数据模式（生产推荐）**
```json
{
  "event": {
    "event_id": "evt_20250901_090005_0001",
    "event_type": {
      "label": "ConversationUtterance",
      "ontology_id": null
    },
    "start_time": "2025-09-01T09:00:05+08:00",
    "end_time": "2025-09-01T09:03:22+08:00",
    "start_offset_sec": 2705.0,
    "end_offset_sec": 2802.0,
    "confidence": 0.89,
    "speakers": [
      {
        "speaker_id": "spk_1",
        "speaker_label": "SPK_1",
        "is_user": true,
        "speaker_confidence": 0.99
      }
    ],
    "transcript": "明早七点去机场，记得身份证和充电宝",
    "audio_features": {
      "avg_volume_db": -18.2,
      "snr_db": 20.5,
      "speech_rate_wpm": 120.0,
      "language": "zh-CN",
      "asr_confidence": 0.87
    },
    "entities": [
      {"type": "time", "value": "明早七点", "confidence": 0.9},
      {"type": "place", "value": "机场", "confidence": 0.95}
    ],
    "privacy": {
      "contains_pii": false,
      "pii_types": [],
      "redaction_suggested": false
    },
    "tags": ["travel", "planning"]
  }
}
```

#### 响应格式

**成功响应 (HTTP 200)**:
```json
{
  // 基础推理结果（必有字段）
  "task_type": "trip",
  "confidence": 0.85,
  "potential_omissions": ["行李", "交通工具"],
  "latency_ms": 1200,
  "model_version": "deepseek:deepseek-chat",
  "summary_text": "很确定这是一个出行安排，不过可能还需要考虑行李、交通工具等细节",
  "suggested_plan": "建议提前一晚准备好证件和行李，设置多个闹钟确保不会睡过头，可以提前预约出租车或安排家人送行，记得查看天气准备合适的衣物，充电宝和数据线也别忘了带上",
  
  // 增强分析结果（仅当输入包含事件数据时）
  "extracted_entities": [
    {"type": "time", "value": "明早七点", "confidence": 0.9},
    {"type": "place", "value": "机场", "confidence": 0.95}
  ],
  "suggested_tags": ["trip", "travel", "planning"],
  "priority_level": "high",
  "reminder_suggestions": ["记得确认行李", "记得确认交通工具"],
  "event_analysis": {
    "has_speakers": true,
    "speaker_count": 1,
    "has_audio_features": true,
    "contains_pii": false,
    "event_duration_sec": 97.0
  },
  "speaker_insights": {
    "total_speakers": 1,
    "user_speakers": 1,
    "multi_speaker": false,
    "primary_speaker": "SPK_1"
  },
  "audio_quality_assessment": {
    "overall_quality": "good",
    "asr_confidence": 0.87,
    "snr_db": 20.5,
    "language": "zh-CN",
    "speech_rate_wpm": 120.0
  },
  "enhanced_nlu": {
    "intents": [
      {
        "intent_name": "travel_planning",
        "score": 0.9,
        "parameters": {"destination": "机场", "time": "明早七点"}
      }
    ],
    "summary": "用户计划明早去机场"
  }
}
```

---

## 📊 数据字段规范

### 请求字段说明

| 字段路径 | 类型 | 必填 | 说明 | 示例 |
|---------|------|------|------|------|
| `text` | string | 条件必填* | 要分析的文本 | "明早七点去机场" |
| `event` | object | 条件必填* | 完整事件数据 | 见上方示例 |
| `event.transcript` | string | 条件必填** | 语音转写文本 | "明早七点去机场" |
| `event.event_id` | string | 推荐 | 事件唯一标识 | "evt_20250901_090005_0001" |
| `event.speakers` | array | 可选 | 说话人信息 | 见上方示例 |
| `event.audio_features` | object | 可选 | 音频特征 | 见上方示例 |
| `event.entities` | array | 可选 | 已识别实体 | 见上方示例 |

*注：`text` 和 `event` 必须提供其中一个  
**注：如果提供 `event`，则 `event.transcript` 必填

### 响应字段说明

#### 基础字段（必有）

| 字段 | 类型 | 说明 | 可能值 |
|------|------|------|--------|
| `task_type` | string | 任务类型 | trip, meeting, shopping, work, health, entertainment, learning, social, finance, other |
| `confidence` | float | 置信度 | 0.0 - 1.0 |
| `potential_omissions` | array | 可能遗漏的信息 | ["时间", "地点", "人员"] |
| `latency_ms` | integer | 处理耗时（毫秒） | 500 - 5000 |
| `model_version` | string | 模型版本 | "deepseek:deepseek-chat" |
| `summary_text` | string | 智能摘要 | "很确定这是一个出行安排..." |
| `suggested_plan` | string | 行动建议 | "建议提前一晚准备好..." |

#### 增强字段（事件数据模式）

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `extracted_entities` | array | 提取的实体 | [{"type": "time", "value": "明早七点"}] |
| `suggested_tags` | array | 建议标签 | ["trip", "travel"] |
| `priority_level` | string | 优先级 | "high", "medium", "low" |
| `reminder_suggestions` | array | 提醒建议 | ["记得确认行李"] |
| `event_analysis` | object | 事件分析 | 见上方示例 |
| `speaker_insights` | object | 说话人洞察 | 见上方示例 |
| `audio_quality_assessment` | object | 音频质量评估 | 见上方示例 |

---

## ⚠️ 错误处理规范

### HTTP状态码

| 状态码 | 说明 | 处理建议 |
|--------|------|----------|
| 200 | 成功 | 正常处理响应数据 |
| 422 | 请求参数错误 | 检查请求格式，必填字段 |
| 502 | 上游服务错误 | 稍后重试，检查网络 |
| 500 | 服务器内部错误 | 联系技术支持 |

### 错误响应格式

```json
{
  "detail": "错误描述信息"
}
```

### 常见错误示例

```json
// 缺少必填字段
{
  "detail": "必须提供 text 字段或 event.transcript 字段"
}

// 推理服务异常
{
  "detail": "上游调用失败: DeepSeek API读取超时，请检查网络连接或稍后重试"
}
```

---

## 🔧 技术规范

### 请求限制
- **单次文本长度**: 最大 2000 字符
- **请求频率**: 建议不超过 10 次/秒
- **超时时间**: 30 秒
- **重试策略**: 建议指数退避，最多重试 3 次

### 认证机制
```http
# 如果启用认证，需要在请求头中包含
Authorization: Bearer your-api-key
```

### CORS支持
API支持跨域请求，允许的方法：GET, POST, OPTIONS

---

## 💻 客户端集成示例

### JavaScript/TypeScript

```typescript
interface PulseWeaveRequest {
  text?: string;
  event?: EventData;
}

interface PulseWeaveResponse {
  task_type: string;
  confidence: number;
  potential_omissions: string[];
  summary_text: string;
  suggested_plan: string;
  // ... 其他字段
}

class PulseWeaveClient {
  constructor(private baseURL: string, private apiKey?: string) {}
  
  async analyze(request: PulseWeaveRequest): Promise<PulseWeaveResponse> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    
    if (this.apiKey) {
      headers['Authorization'] = `Bearer ${this.apiKey}`;
    }
    
    const response = await fetch(`${this.baseURL}/infer`, {
      method: 'POST',
      headers,
      body: JSON.stringify(request)
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(`API Error: ${error.detail}`);
    }
    
    return response.json();
  }
}

// 使用示例
const client = new PulseWeaveClient('http://localhost:8000');

// 简单文本分析
const result1 = await client.analyze({
  text: '明天开会记得带资料'
});

// 完整事件分析
const result2 = await client.analyze({
  event: eventData
});
```

### Python

```python
import httpx
from typing import Dict, Any, Optional

class PulseWeaveClient:
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
    
    async def analyze(self, text: str = None, event: Dict[str, Any] = None) -> Dict[str, Any]:
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        
        payload = {}
        if text:
            payload['text'] = text
        if event:
            payload['event'] = event
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f'{self.base_url}/infer',
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()

# 使用示例
client = PulseWeaveClient('http://localhost:8000')
result = await client.analyze(text='明天开会记得带资料')
```

---

## 📋 集成检查清单

### 开发阶段
- [ ] 确认API地址和端口
- [ ] 测试健康检查接口
- [ ] 实现简单文本模式
- [ ] 处理基础错误情况
- [ ] 添加超时和重试机制

### 测试阶段
- [ ] 测试各种文本类型
- [ ] 验证错误处理逻辑
- [ ] 性能压力测试
- [ ] 网络异常测试

### 生产部署
- [ ] 配置生产环境地址
- [ ] 设置API密钥（如需要）
- [ ] 配置监控和日志
- [ ] 制定降级策略

---

## 🚀 版本兼容性

### 当前版本: v1.0
### 向后兼容承诺:
- 基础字段（task_type, confidence等）保持稳定
- 新增字段不会影响现有集成
- 重大变更会提前通知并提供迁移指南

### 升级路径:
1. **阶段1**: 使用简单文本模式集成
2. **阶段2**: 逐步迁移到事件数据模式
3. **阶段3**: 利用增强分析功能

---

## 🎯 任务类型说明

系统支持以下10种任务类型：

| 类型 | 英文标识 | 说明 | 示例 |
|------|----------|------|------|
| 出行安排 | trip | 旅行、出差、交通安排 | "明早去机场" |
| 会议安排 | meeting | 会议、讨论、汇报 | "下午开会" |
| 购物计划 | shopping | 购买、采购、消费 | "去超市买菜" |
| 工作任务 | work | 项目、任务、工作安排 | "完成报告" |
| 健康事务 | health | 医疗、体检、健康管理 | "明天体检" |
| 娱乐活动 | entertainment | 娱乐、运动、休闲 | "看电影" |
| 学习计划 | learning | 学习、培训、教育 | "复习考试" |
| 社交活动 | social | 聚会、社交、人际交往 | "和朋友聚餐" |
| 财务事务 | finance | 理财、支付、财务管理 | "还信用卡" |
| 其他事务 | other | 未分类的其他任务 | 兜底分类 |

---

## 📞 技术支持

- **文档地址**: [API_USAGE.md](API_USAGE.md)
- **工作流程**: [WORKFLOW.md](WORKFLOW.md)
- **项目结构**: [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)
- **快速开始**: [QUICKSTART.md](QUICKSTART.md)

---

**协议版本**: v1.0  
**最后更新**: 2025-01-05  
**维护团队**: PulseWeave开发团队
