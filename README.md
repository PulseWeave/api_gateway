# PulseWeave API Gateway

🌊 基于语音的智能备忘和建议工具 - AI推理服务网关

## 功能特性

- 🎯 **智能任务分类**: 识别10种常见任务类型（出行、会议、购物等）
- 🔍 **遗漏检测**: 发现可能遗漏的关键信息
- 💡 **行动建议**: 提供人性化的具体建议
- 🏷️ **实体提取**: 从语音事件中提取时间、地点、人物等关键信息
- ⚡ **优先级评估**: 自动评估任务优先级
- 🎵 **音频质量分析**: 评估语音识别质量和音频特征
- 👥 **说话人分析**: 支持多说话人场景分析
- 🎨 **可视化界面**: 提供基础和高级两种演示界面
- 🔐 **安全认证**: 可选的API密钥认证机制

## 快速开始

### 1. 安装和配置

```bash
# 进入API网关目录
cd api_gateway

# 使用启动脚本安装依赖
python start_server.py --install-deps

# 复制配置文件
cp config.example.yaml config.yaml

# 编辑配置文件，设置API密钥等信息
# 或设置环境变量: export DEEPSEEK_API_KEY=your-key
```

### 2. 启动服务

```bash
# 开发模式（自动重载）
python start_server.py --reload

# 生产模式
python start_server.py --workers 4

# 检查配置
python start_server.py --check-only
```

### 3. 访问界面

- **基础界面**: http://localhost:8000/ui/
- **高级界面**: http://localhost:8000/ui/advanced_demo.html
- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

## 架构设计

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web界面       │    │   API Gateway    │    │  推理服务       │
│                 │    │                  │    │                 │
│ • 基础演示界面  │◄──►│ • REST API       │◄──►│ • 云端推理      │
│ • 高级演示界面  │    │ • WebSocket      │    │ • 外部提供商    │
│ • 实时监控      │    │ • 批量处理       │    │ • 模型管理      │
└─────────────────┘    │ • 认证授权       │    └─────────────────┘
                       │ • 健康检查       │
                       └──────────────────┘
```

## API 接口

### HTTP接口（同步）

- `POST /infer` - 智能推理接口（支持文本和事件数据两种模式）
- `GET /health` - 服务健康检查
- `GET /` - 重定向到演示界面

### WebSocket接口（异步实时）

- `WS /ws` - WebSocket连接端点
  - 异步任务提交和处理
  - 实时状态通知
  - 任务队列管理
  - 统计信息查询
- `GET /ws/stats` - WebSocket统计信息

### 两种输入模式

#### 简单文本模式（向后兼容）
```json
{
  "text": "明早七点去机场，记得身份证和充电宝"
}
```

#### 完整事件数据模式（生产推荐）
```json
{
  "event": {
    "event_id": "evt_20250901_090005_0001",
    "transcript": "明早七点去机场，记得身份证和充电宝",
    "speakers": [...],
    "audio_features": {...},
    "entities": [...]
  }
}
```

## 推理能力

### 支持的任务类型

- 🧳 **出行安排** (trip): 旅行、出差、交通安排
- 🤝 **会议安排** (meeting): 会议、讨论、汇报
- 🛒 **购物计划** (shopping): 购买、采购、消费
- 💼 **工作任务** (work): 项目、任务、工作安排
- 🏥 **健康事务** (health): 医疗、体检、健康管理
- 🎮 **娱乐活动** (entertainment): 娱乐、运动、休闲
- 📚 **学习计划** (learning): 学习、培训、教育
- 👥 **社交活动** (social): 聚会、社交、人际交往
- 💰 **财务事务** (finance): 理财、支付、财务管理
- 📋 **其他事务** (other): 未分类的其他任务

### 智能分析功能

#### 基础分析（所有模式）
- **任务分类**: 自动识别文本所属的任务类型
- **置信度评估**: 提供分类结果的可信度评分
- **遗漏检测**: 识别可能遗漏的关键信息
- **智能摘要**: 生成简洁的结果总结
- **行动建议**: 提供具体的执行计划建议

#### 增强分析（事件数据模式）
- **实体提取**: 从事件数据中提取时间、地点、人物等关键信息
- **优先级评估**: 基于置信度自动评估任务优先级
- **标签建议**: 基于任务类型和内容建议标签
- **提醒生成**: 基于遗漏项生成具体提醒
- **说话人分析**: 分析多说话人场景
- **音频质量评估**: 评估语音识别质量和音频特征

## 配置说明

### 基础配置 (config.yaml)

```yaml
provider:
  name: deepseek          # 提供商: deepseek, openai, dummy
  mode: http              # 模式: http, sdk
  base_url: https://api.deepseek.com
  model: deepseek-chat
  api_key: your-api-key   # 或通过环境变量设置
  timeout_sec: 8
  max_retries: 2
  temperature: 0.0
  max_tokens: 300

service:
  require_auth: false     # 是否需要认证
  return_vector: false    # 是否返回向量表示
```

### 环境变量

```bash
# API配置
export API_CONFIG=/path/to/config.yaml
export GATEWAY_API_KEY=your-gateway-key

# 外部提供商密钥
export DEEPSEEK_API_KEY=your-deepseek-key
export OPENAI_API_KEY=your-openai-key
```

## 测试工具

### 运行完整测试

```bash
# 测试所有接口
python test_api.py --url http://localhost:8000

# 测试特定功能
python test_api.py --test health
python test_api.py --test infer
python test_api.py --test batch
python test_api.py --test websocket

# 使用认证测试
python test_api.py --token your-api-key
```

### 启动脚本测试

```bash
# 运行测试后退出
python start_server.py --test

# 测试远程服务
python start_server.py --test --test-url http://remote-server:8000
```

## 部署指南

### 开发环境

```bash
# 启动开发服务器
python start_server.py --reload --log-level debug
```

### 生产环境

```bash
# 多进程部署
python start_server.py --workers 4 --host 0.0.0.0 --port 8000

# 或使用uvicorn直接启动
uvicorn server:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker 部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "start_server.py", "--workers", "4"]
```

## 故障排除

### 常见问题

1. **服务启动失败**
   ```bash
   # 检查配置
   python start_server.py --check-only

   # 检查依赖
   pip install -r requirements.txt
   ```

2. **推理超时**
   - 增加配置中的 `timeout_sec`
   - 检查网络连接和API密钥
   - 尝试使用云端推理模式

3. **WebSocket连接失败**
   - 检查防火墙设置
   - 确认代理配置支持WebSocket
   - 验证服务器WebSocket支持

### 获取帮助

- 📖 **API对接协议**: [API_PROTOCOL.md](API_PROTOCOL.md) - Web端对接必读
- 📖 **详细使用文档**: [API_USAGE.md](API_USAGE.md)
- 🔄 **工作流程详解**: [WORKFLOW.md](WORKFLOW.md)
- 🏗️ **项目结构说明**: [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)
- 🚀 **快速开始指南**: [QUICKSTART.md](QUICKSTART.md)
- 🔍 **启用调试日志**: `--log-level debug`
- 📊 **查看API文档**: http://localhost:8000/docs

## 📋 文档导航

| 文档 | 用途 | 适用人群 |
|------|------|----------|
| [API_PROTOCOL.md](API_PROTOCOL.md) | 🤝 **HTTP API对接协议** | **Web端开发者必读** |
| [WEBSOCKET_PROTOCOL.md](WEBSOCKET_PROTOCOL.md) | 🔄 **WebSocket实时协议** | **需要异步推理的开发者** |
| [QUICKSTART.md](QUICKSTART.md) | 🚀 5分钟快速体验 | 新用户 |
| [API_USAGE.md](API_USAGE.md) | 📖 详细API使用说明 | 开发者 |
| [WORKFLOW.md](WORKFLOW.md) | 🔄 完整工作流程详解 | 架构师、产品经理 |
| [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) | 🏗️ 项目结构和扩展指南 | 维护者、贡献者 |

---

🌊 **PulseWeave** - 让AI推理如潮水般流畅自然