# PulseWeave API Gateway 使用文档

## 概述

PulseWeave API Gateway 是一个基于语音的智能备忘和建议工具的推理服务网关。它接收文本或完整的语音事件数据，使用DeepSeek AI进行智能分析，提供任务分类、遗漏检测、行动建议等功能。

## 核心功能

- 🎯 **智能任务分类**: 识别10种常见任务类型
- 🔍 **遗漏检测**: 发现可能遗漏的关键信息
- 💡 **行动建议**: 提供人性化的具体建议
- 🏷️ **实体提取**: 从事件数据中提取关键实体
- ⚡ **优先级评估**: 自动评估任务优先级
- 🎵 **音频质量分析**: 评估语音识别质量
- 👥 **说话人分析**: 多说话人场景分析

## 快速开始

### 1. 安装依赖

```bash
cd api_gateway
pip install -r requirements.txt
```

### 2. 配置服务

复制配置文件并修改：
```bash
cp config.example.yaml config.yaml
```

编辑 `config.yaml`：
```yaml
provider:  
  name: deepseek  # 或 openai, dummy
  mode: http      # 或 sdk
  base_url: https://api.deepseek.com
  model: deepseek-chat
  api_key: your-api-key-here
  timeout_sec: 8
  max_retries: 2
  temperature: 0.0
  max_tokens: 300

service:  
  require_auth: false  # 是否需要认证
  return_vector: false # 是否返回向量表示
```

### 3. 启动服务

```bash
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 访问界面

- 基础界面: http://localhost:8000/ui/
- 高级界面: http://localhost:8000/ui/advanced_demo.html
- API文档: http://localhost:8000/docs

## API 接口

### 健康检查

**GET** `/health`

返回服务健康状态。

```json
{
  "status": "ok"
}
```

### 智能推理接口

**POST** `/infer`

支持两种输入模式：简单文本模式和完整事件数据模式。

#### 模式1：简单文本推理（向后兼容）

请求体：
```json
{
  "text": "明早七点去机场，记得身份证和充电宝"
}
```

#### 模式2：完整事件数据推理

请求体：
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
    "tags": ["travel", "planning"]
  }
}
```

#### 统一响应格式

```json
{
  // 基础推理结果
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
  }
}
```

### 云端推理

**POST** `/infer/cloud`

使用本地云端推理服务。

请求体格式同 `/infer`，但会使用本地模型进行推理。

### 批量推理

**POST** `/infer/batch`

批量处理多个文本。

请求体：
```json
{
  "texts": [
    "明天开会记得带资料",
    "周末去超市买菜",
    "下周体检预约医院"
  ],
  "use_cloud_inference": true  // 可选，是否使用云端推理
}
```

响应：
```json
{
  "results": [
    {
      "task_type": "meeting",
      "confidence": 0.78,
      // ... 其他字段
    }
    // ... 更多结果
  ],
  "total_count": 3,
  "success_count": 3,
  "total_latency_ms": 2500
}
```

### 模型状态

**GET** `/model/status`

获取模型加载状态和配置信息。

```json
{
  "cloud_inference": {
    "initialized": true,
    "device": "cuda:0",
    "loaded_models": ["classifier", "vector", "bert"],
    "available_task_types": ["trip", "meeting", "shopping", "work", "health", "entertainment", "learning", "social", "finance", "other"],
    "model_version": "cloud:pulseweave-v1.0"
  },
  "external_provider": {
    "name": "deepseek",
    "model": "deepseek-chat",
    "available": true
  },
  "service_config": {
    "require_auth": false,
    "return_vector": false
  }
}
```

### 模型健康检查

**GET** `/model/health`

执行完整的模型健康检查，包括推理测试。

```json
{
  "overall_status": "healthy",
  "cloud_inference": {
    "status": "healthy",
    "test_inference": "passed",
    "latency_ms": 150
  },
  "external_provider": {
    "status": "healthy", 
    "test_inference": "passed",
    "latency_ms": 1200
  },
  "timestamp": 1703123456
}
```

## WebSocket 接口

### 连接

连接到 `ws://localhost:8000/ws`

### 消息格式

所有消息都是JSON格式。

#### 心跳检测

发送：
```json
{
  "type": "ping"
}
```

接收：
```json
{
  "type": "pong",
  "timestamp": 1703123456
}
```

#### 单文本推理

发送：
```json
{
  "type": "infer",
  "text": "要分析的文本",
  "use_cloud": false  // 可选
}
```

接收（开始）：
```json
{
  "type": "infer_start",
  "text": "要分析的文本"
}
```

接收（结果）：
```json
{
  "type": "infer_result",
  "result": {
    "task_type": "trip",
    "confidence": 0.85,
    // ... 完整推理结果
  }
}
```

#### 批量推理

发送：
```json
{
  "type": "batch_infer",
  "texts": ["文本1", "文本2", "文本3"],
  "use_cloud": false
}
```

接收（开始）：
```json
{
  "type": "batch_start",
  "total_count": 3
}
```

接收（进度）：
```json
{
  "type": "batch_progress",
  "completed": 1,
  "total": 3,
  "current_result": {
    "index": 0,
    "text": "文本1",
    "result": { /* 推理结果 */ }
  }
}
```

接收（完成）：
```json
{
  "type": "batch_complete",
  "results": [ /* 所有结果 */ ],
  "total_count": 3,
  "success_count": 3
}
```

## 认证

如果配置中启用了认证（`require_auth: true`），需要在请求头中包含认证信息：

```
Authorization: Bearer your-api-key
```

环境变量设置：
```bash
export GATEWAY_API_KEY=your-secret-key
```

## 任务类型

系统支持以下任务类型：

- `trip`: 出行安排
- `meeting`: 会议安排  
- `shopping`: 购物计划
- `work`: 工作任务
- `health`: 健康事务
- `entertainment`: 娱乐活动
- `learning`: 学习计划
- `social`: 社交活动
- `finance`: 财务事务
- `other`: 其他事务

## 错误处理

### HTTP 状态码

- `200`: 成功
- `401`: 认证失败
- `422`: 请求参数错误
- `502`: 上游服务错误

### 错误响应格式

```json
{
  "detail": "错误描述信息"
}
```

## 性能优化

### 批量推理

- 单次批量推理最多支持100个文本
- 建议批量大小为10-50个文本以获得最佳性能
- 使用WebSocket可以获得实时进度反馈

### 缓存

- 系统会缓存模型加载状态
- 相同文本的推理结果可能被缓存（取决于提供商）

### 超时设置

- 单文本推理默认超时：30秒
- 批量推理默认超时：60秒
- WebSocket连接超时：10秒

## 监控和调试

### 日志

服务日志包含详细的请求和响应信息，可用于调试。

### 测试工具

使用内置测试脚本：

```bash
python test_api.py --url http://localhost:8000 --test all
```

测试选项：
- `--test health`: 只测试健康检查
- `--test infer`: 测试推理接口
- `--test batch`: 测试批量推理
- `--test status`: 测试状态接口
- `--test websocket`: 测试WebSocket
- `--test all`: 运行所有测试（默认）

### 性能指标

通过高级演示界面可以查看：
- 总请求数
- 平均延迟
- 成功率
- 系统健康状态

## 部署建议

### 生产环境

1. 启用认证：设置 `require_auth: true`
2. 配置HTTPS：使用反向代理（如Nginx）
3. 设置合适的超时时间
4. 配置日志轮转
5. 监控系统资源使用

### Docker部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 环境变量

```bash
# API配置
export API_CONFIG=/path/to/config.yaml
export GATEWAY_API_KEY=your-secret-key

# 外部提供商
export DEEPSEEK_API_KEY=your-deepseek-key
export OPENAI_API_KEY=your-openai-key
```

## 故障排除

### 常见问题

1. **模型加载失败**
   - 检查模型文件路径
   - 确认GPU/CPU资源充足
   - 查看详细错误日志

2. **推理超时**
   - 增加超时时间配置
   - 检查网络连接
   - 验证API密钥有效性

3. **WebSocket连接失败**
   - 确认防火墙设置
   - 检查代理配置
   - 验证WebSocket支持

4. **认证失败**
   - 检查API密钥配置
   - 确认请求头格式正确
   - 验证环境变量设置

### 获取帮助

- 查看服务日志：`uvicorn server:app --log-level debug`
- 运行测试脚本：`python test_api.py`
- 检查API文档：访问 `/docs` 端点
