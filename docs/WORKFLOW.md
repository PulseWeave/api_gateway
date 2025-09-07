# PulseWeave API Gateway 工作流程详解

## 🎯 项目定位

PulseWeave是一个**基于语音的智能备忘和建议工具**，API Gateway是其核心推理服务，负责：
- 接收语音转写文本或完整事件数据
- 使用DeepSeek AI进行智能分析
- 提供任务分类、遗漏检测、行动建议等功能

## 📊 数据流程图

```
语音设备/应用 → ASR转写 → 事件数据 → API Gateway → DeepSeek AI → 智能分析结果
     ↓              ↓         ↓           ↓            ↓           ↓
   录音文件      转写文本    JSON事件    推理请求     AI分析     增强结果
```

## 🔄 完整工作流程

### 第1步：数据输入
**两种输入模式**：

#### 模式A：简单文本（适合快速测试）
```json
{
  "text": "明早七点去机场，记得身份证和充电宝"
}
```

#### 模式B：完整事件数据（生产环境推荐）
```json
{
  "event": {
    "event_id": "evt_20250901_090005_0001",
    "transcript": "明早七点去机场，记得身份证和充电宝",
    "speakers": [...],
    "audio_features": {...},
    "entities": [...],
    // 完整的语音事件结构
  }
}
```

### 第2步：文本提取
API Gateway会自动提取要分析的文本：
- 如果有`text`字段 → 直接使用
- 如果只有`event.transcript` → 使用transcript
- 如果都没有 → 返回422错误

### 第3步：DeepSeek AI分析
使用优化的prompt调用DeepSeek API：
```
系统角色：贴心的AI生活助理
用户输入：要分析的文本
分析要求：
- 识别任务类型（10种预定义类型）
- 评估置信度
- 检测可能遗漏的信息
- 生成人性化摘要
- 提供实用的行动建议
```

### 第4步：结果增强
如果输入包含事件数据，会进行额外分析：

#### 4.1 实体提取
从事件数据中提取已识别的实体：
```json
"extracted_entities": [
  {"type": "time", "value": "明早七点", "confidence": 0.9},
  {"type": "place", "value": "机场", "confidence": 0.95}
]
```

#### 4.2 标签建议
基于任务类型和现有标签生成建议：
```json
"suggested_tags": ["trip", "travel", "planning"]
```

#### 4.3 优先级评估
基于AI置信度自动评估：
- confidence > 0.8 → "high"
- confidence 0.4-0.8 → "medium"  
- confidence < 0.4 → "low"

#### 4.4 提醒生成
基于遗漏项生成具体提醒：
```json
"reminder_suggestions": ["记得确认行李", "记得确认交通工具"]
```

#### 4.5 事件分析
分析事件的基本特征：
```json
"event_analysis": {
  "speaker_count": 1,
  "event_duration_sec": 97.0,
  "contains_pii": false,
  "has_audio_features": true
}
```

#### 4.6 说话人洞察
分析多说话人场景：
```json
"speaker_insights": {
  "total_speakers": 1,
  "user_speakers": 1,
  "multi_speaker": false,
  "primary_speaker": "SPK_1"
}
```

#### 4.7 音频质量评估
评估ASR质量：
```json
"audio_quality_assessment": {
  "overall_quality": "good",
  "asr_confidence": 0.87,
  "snr_db": 20.5
}
```

### 第5步：结果返回
返回完整的分析结果，包含：
- 基础推理结果（向后兼容）
- 增强分析结果（仅当有事件数据时）

## 🏗️ 系统架构

### 核心组件

1. **FastAPI服务器** (`server.py`)
   - 接收HTTP请求
   - 参数验证和错误处理
   - 调用推理服务

2. **DeepSeek Provider** (`providers/deepseek_provider.py`)
   - 封装DeepSeek API调用
   - 处理超时和重试
   - 提供备用规则引擎

3. **数据模型** (`schemas.py`)
   - 定义完整的事件数据结构
   - 请求/响应验证
   - 类型安全保证

4. **Prompt模板** (`prompt_templates.py`)
   - 优化的AI提示词
   - 任务类型定义
   - 遗漏检测规则

### 配置文件 (`config.yaml`)
```yaml
provider:
  name: deepseek
  mode: http
  base_url: https://api.deepseek.com
  model: deepseek-chat
  api_key: your-api-key
  timeout_sec: 30
  temperature: 0.0
  max_tokens: 300

service:
  require_auth: false
  return_vector: false
```

## 🎨 前端界面

### 基础界面 (`static/index.html`)
- 简单的文本输入测试
- 结果展示和调试
- 增强信息可视化

### 高级界面 (`static/advanced_demo.html`)
- 多标签页设计
- 实时推理测试
- 配置管理

## 🔧 部署和使用

### 启动服务
```bash
cd api_gateway
python start_server.py --reload
```

### 访问界面
- 基础界面: http://localhost:8000/ui/
- API文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

### API调用示例
```python
import httpx

# 简单文本推理
response = httpx.post("http://localhost:8000/infer", 
                     json={"text": "明天开会记得带资料"})

# 完整事件数据推理
response = httpx.post("http://localhost:8000/infer", 
                     json={"event": event_data})
```

## 🎯 使用场景

### 场景1：语音备忘录
用户说："明天下午三点和张总开会，记得带上项目报告"
→ 系统识别为会议安排，提醒准备材料和确认时间地点

### 场景2：出行计划
用户说："下周去北京出差，要订机票和酒店"
→ 系统识别为出行安排，提醒检查证件、查看天气、准备行李

### 场景3：购物清单
用户说："周末去超市买菜，需要买米、油、蔬菜"
→ 系统识别为购物计划，提醒制定详细清单和预算

## 🔍 关键特性

### 1. 向后兼容
- 支持简单的`{"text": "..."}`格式
- 现有集成无需修改

### 2. 渐进增强
- 可以逐步从简单模式升级到完整模式
- 事件数据越丰富，分析结果越详细

### 3. 智能分析
- 不仅仅是文本分类，还提供实用的行动建议
- 考虑语音质量、说话人信息等上下文

### 4. 人性化输出
- 避免机械化的回复
- 像朋友一样的贴心建议

## 🚀 扩展方向

1. **更多任务类型**: 可以扩展支持更多领域的任务
2. **多语言支持**: 支持英文、粤语等其他语言
3. **个性化学习**: 基于用户历史调整建议风格
4. **集成外部服务**: 连接日历、地图、天气等API

这就是PulseWeave API Gateway的完整工作流程！它将简单的语音文本转化为智能的、可执行的建议。
