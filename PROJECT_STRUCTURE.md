# PulseWeave API Gateway 项目结构

## 📁 目录结构

```
api_gateway/
├── 📄 server.py                    # 主服务器文件 - FastAPI应用
├── 📄 schemas.py                   # 数据模型定义 - Pydantic模型
├── 📄 prompt_templates.py          # AI提示词模板
├── 📄 start_server.py             # 启动脚本
├── 📄 config.yaml                 # 配置文件
├── 📄 config.example.yaml         # 配置文件示例
├── 📄 requirements.txt            # Python依赖
├── 📄 .env.example                # 环境变量示例
├── 📄 README.md                   # 项目说明
├── 📄 API_USAGE.md               # API使用文档
├── 📄 WORKFLOW.md                # 工作流程详解
├── 📄 QUICKSTART.md              # 快速开始指南
├── 📄 PROJECT_STRUCTURE.md       # 项目结构说明（本文件）
├── 📁 providers/                  # 推理提供商模块
│   ├── 📄 __init__.py
│   ├── 📄 base.py                 # 基础提供商接口
│   ├── 📄 dummy_provider.py       # 测试用虚拟提供商
│   ├── 📄 deepseek_provider.py    # DeepSeek API提供商
│   └── 📄 openai_provider.py      # OpenAI API提供商
└── 📁 static/                     # 静态文件（前端界面）
    ├── 📄 index.html              # 基础演示界面
    └── 📄 advanced_demo.html      # 高级演示界面
```

## 🔧 核心文件说明

### 1. `server.py` - 主服务器
**作用**: FastAPI应用的入口点
**核心功能**:
- 定义API路由 (`/health`, `/infer`)
- 处理请求验证和错误处理
- 调用推理提供商
- 增强事件数据分析

**关键代码**:
```python
@app.post("/infer", response_model=InferResponse)
async def infer(request: InferRequest):
    # 提取文本和事件数据
    # 调用DeepSeek API
    # 增强分析结果
    # 返回完整响应
```

### 2. `schemas.py` - 数据模型
**作用**: 定义所有的数据结构
**核心模型**:
- `EventData`: 完整的语音事件数据结构
- `InferRequest`: API请求格式
- `InferResponse`: API响应格式
- `Speaker`, `AudioFeatures`, `Entity`等子模型

**关键特性**:
- 使用Pydantic进行数据验证
- 支持可选字段和默认值
- 类型安全保证

### 3. `providers/deepseek_provider.py` - DeepSeek集成
**作用**: 封装DeepSeek API调用
**核心功能**:
- HTTP/SDK两种调用模式
- 超时和重试机制
- 错误处理和回退
- 人性化建议生成

**关键方法**:
```python
async def predict(self, text: str, event_data: Dict = None):
    # 调用DeepSeek API
    # 解析JSON响应
    # 补充缺失字段
    # 返回标准格式
```

### 4. `prompt_templates.py` - AI提示词
**作用**: 定义DeepSeek AI的提示词模板
**核心内容**:
- 系统角色定义（贴心的AI助理）
- 任务类型列表（10种预定义类型）
- 遗漏检测规则
- 输出格式要求

**关键特性**:
- 人性化的角色设定
- 具体的示例指导
- 严格的JSON输出要求

### 5. `config.yaml` - 配置文件
**作用**: 系统配置参数
**主要配置**:
```yaml
provider:
  name: deepseek              # 提供商名称
  api_key: your-key          # API密钥
  timeout_sec: 30            # 超时时间
  temperature: 0.0           # AI生成温度

service:
  require_auth: false        # 是否需要认证
```

## 🎯 数据流向

### 输入处理流程
```
HTTP请求 → server.py → schemas.py验证 → providers/deepseek_provider.py → DeepSeek API
```

### 输出增强流程
```
DeepSeek响应 → 基础结果 → 事件数据分析 → 增强结果 → schemas.py验证 → HTTP响应
```

## 🔄 关键工作流程

### 1. 请求接收 (`server.py`)
```python
# 1. 接收HTTP POST请求
# 2. 使用schemas.py验证数据格式
# 3. 提取文本内容（text或event.transcript）
# 4. 调用推理提供商
```

### 2. AI推理 (`providers/deepseek_provider.py`)
```python
# 1. 构建prompt（使用prompt_templates.py）
# 2. 调用DeepSeek API
# 3. 解析JSON响应
# 4. 补充缺失字段（备用规则引擎）
```

### 3. 结果增强 (`server.py`)
```python
# 1. 提取事件数据中的实体
# 2. 生成建议标签
# 3. 评估优先级
# 4. 分析说话人和音频质量
# 5. 生成提醒建议
```

### 4. 响应返回 (`schemas.py`)
```python
# 1. 使用InferResponse模型验证
# 2. 确保所有字段都有值
# 3. 返回JSON响应
```

## 🎨 前端界面

### `static/index.html` - 基础界面
**功能**:
- 简单的文本输入框
- 推理结果展示
- 增强信息可视化
- 调试信息显示

**适用场景**: 开发测试、快速验证

### `static/advanced_demo.html` - 高级界面
**功能**:
- 多标签页设计
- 配置管理
- 更丰富的结果展示

**适用场景**: 演示展示、功能测试

## 🔧 配置和部署

### 环境变量
```bash
# API密钥
export DEEPSEEK_API_KEY=your-deepseek-key
export OPENAI_API_KEY=your-openai-key

# 服务配置
export GATEWAY_API_KEY=your-gateway-key
export API_CONFIG=/path/to/config.yaml
```

### 启动方式
```bash
# 开发模式
python start_server.py --reload

# 生产模式
python start_server.py --workers 4

# 直接使用uvicorn
uvicorn server:app --host 0.0.0.0 --port 8000
```

## 📊 扩展点

### 1. 添加新的推理提供商
1. 在`providers/`目录创建新文件
2. 继承`BaseProvider`类
3. 实现`predict`方法
4. 在`providers/__init__.py`中注册

### 2. 扩展任务类型
1. 修改`prompt_templates.py`中的`TASK_TYPES`
2. 更新`FORGET_RULES`添加新的遗漏检测规则
3. 在`deepseek_provider.py`中添加对应的建议模板

### 3. 增强事件分析
1. 在`server.py`的`_enhance_with_event_analysis`函数中添加新的分析逻辑
2. 更新`schemas.py`中的响应模型
3. 修改前端界面显示新的分析结果

## 🔍 调试和监控

### 日志查看
```bash
# 启动时指定日志级别
python start_server.py --log-level debug
```

### 健康检查
```bash
curl http://localhost:8000/health
```

### API文档
访问 http://localhost:8000/docs 查看自动生成的API文档

这个项目结构设计简洁清晰，每个文件都有明确的职责，便于维护和扩展。
