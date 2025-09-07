# PulseWeave API Gateway 快速启动指南

## 🚀 5分钟快速体验

### 第一步：安装依赖

```bash
cd api_gateway
python start_server.py --install-deps
```

### 第二步：配置服务

```bash
# 复制配置文件
cp config.example.yaml config.yaml

# 设置API密钥（选择其中一种方式）
# 方式1：环境变量
export DEEPSEEK_API_KEY=your-deepseek-api-key

# 方式2：直接编辑config.yaml文件
# 在provider.api_key字段填入你的API密钥
```

### 第三步：启动服务

```bash
# 开发模式启动（推荐）
python start_server.py --reload
```

### 第四步：测试功能

```bash
# 健康检查
curl http://localhost:8000/health

# 简单推理测试
curl -X POST http://localhost:8000/infer \
  -H "Content-Type: application/json" \
  -d '{"text": "明早七点去机场，记得身份证和充电宝"}'
```

### 第五步：访问界面

打开浏览器访问：
- **基础界面**: http://localhost:8000/ui/
- **API文档**: http://localhost:8000/docs
- **API协议文档**: [API_PROTOCOL.md](API_PROTOCOL.md)

## 🎯 快速测试

### 在演示界面测试

1. 打开高级演示界面
2. 在"单文本推理"标签页输入测试文本：
   ```
   明早七点去机场，记得身份证和充电宝
   ```
3. 点击"开始推理"按钮
4. 查看推理结果和智能建议

### 使用API测试

```bash
# 运行自动化测试
python test_api.py

# 或者使用curl测试
curl -X POST http://localhost:8000/infer \
  -H "Content-Type: application/json" \
  -d '{"text": "明早七点去机场，记得身份证和充电宝"}'
```

## 🔧 配置选项

### 基础配置 (config.yaml)

```yaml
provider:
  name: deepseek          # 推理提供商
  mode: http              # 连接模式
  base_url: https://api.deepseek.com
  model: deepseek-chat
  api_key: your-api-key   # API密钥
  timeout_sec: 8          # 超时时间
  temperature: 0.0        # 生成温度

service:
  require_auth: false     # 是否需要认证
  return_vector: false    # 是否返回向量
```

### 支持的提供商

- **DeepSeek**: 设置 `DEEPSEEK_API_KEY`
- **OpenAI**: 设置 `OPENAI_API_KEY`，修改配置中的 `provider.name` 为 `openai`
- **Dummy**: 用于测试，无需API密钥

## 📊 功能演示

### 1. 单文本推理

输入：`下周三下午两点开项目评审会`

输出：
```json
{
  "task_type": "meeting",
  "confidence": 0.85,
  "potential_omissions": ["参会人", "会议室", "材料"],
  "summary_text": "识别为会议安排，置信度高（0.85）",
  "suggested_plan": "1. 确认会议时间、地点和参会人员；2. 准备会议议程和相关材料..."
}
```

### 2. 批量推理

在高级界面的"批量推理"标签页，输入多行文本：
```
明天开会记得带资料
周末去超市买菜
下周体检预约医院
```

系统会并行处理所有文本并显示结果。

### 3. 实时WebSocket

高级界面支持WebSocket实时通信，可以看到推理进度和实时结果。

### 4. 系统监控

在"系统监控"标签页可以查看：
- 服务健康状态
- 模型加载状态
- 性能指标统计

## 🛠️ 高级功能

### 云端推理模式

如果你有本地模型，可以使用云端推理：

```bash
# 在API调用中指定使用云端推理
curl -X POST http://localhost:8000/infer/cloud \
  -H "Content-Type: application/json" \
  -d '{"text": "测试云端推理"}'
```

### 批量推理API

```bash
curl -X POST http://localhost:8000/infer/batch \
  -H "Content-Type: application/json" \
  -d '{
    "texts": [
      "明天开会记得带资料",
      "周末去超市买菜"
    ]
  }'
```

### WebSocket连接

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

// 发送推理请求
ws.send(JSON.stringify({
  type: 'infer',
  text: '要分析的文本'
}));

// 接收结果
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
};
```

## 🔍 故障排除

### 常见问题

1. **服务启动失败**
   ```bash
   # 检查配置
   python start_server.py --check-only
   ```

2. **API密钥错误**
   - 检查环境变量是否设置正确
   - 确认config.yaml中的api_key字段
   - 验证API密钥是否有效

3. **推理超时**
   - 增加config.yaml中的timeout_sec值
   - 检查网络连接
   - 尝试使用dummy提供商测试

4. **界面无法访问**
   - 确认服务已启动
   - 检查端口是否被占用
   - 尝试访问 http://localhost:8000/health

### 获取帮助

```bash
# 查看启动脚本帮助
python start_server.py --help

# 运行完整测试
python test_api.py --url http://localhost:8000

# 查看详细日志
python start_server.py --reload --log-level debug
```

## 📈 性能优化

### 生产环境部署

```bash
# 多进程模式
python start_server.py --workers 4 --host 0.0.0.0

# 启用认证
# 在config.yaml中设置 require_auth: true
# 设置环境变量 GATEWAY_API_KEY=your-secret-key
```

### 批量处理优化

- 单次批量推理建议10-50个文本
- 使用WebSocket获得实时进度反馈
- 合理设置超时时间

## 🎨 界面功能

### 高级演示界面特性

- **多标签页设计**: 单文本、批量、监控、设置
- **实时进度显示**: 批量推理进度条和状态更新
- **结果可视化**: 置信度、任务类型、性能指标
- **导出功能**: 批量结果可导出为JSON文件
- **设置管理**: API地址、认证、主题等配置
- **键盘快捷键**: Ctrl+Enter执行推理，Ctrl+1-4切换标签

### 监控面板

- **健康状态**: 云端推理和外部提供商状态
- **性能指标**: 请求数、平均延迟、成功率
- **模型信息**: 加载状态、设备信息、支持的任务类型

## 🔗 集成示例

### Python客户端

```python
import requests

class PulseWeaveClient:
    def __init__(self, base_url="http://localhost:8000", token=None):
        self.base_url = base_url
        self.headers = {"Content-Type": "application/json"}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
    
    def infer(self, text, use_cloud=False):
        endpoint = "/infer/cloud" if use_cloud else "/infer"
        response = requests.post(
            f"{self.base_url}{endpoint}",
            headers=self.headers,
            json={"text": text}
        )
        return response.json()
    
    def batch_infer(self, texts, use_cloud=False):
        response = requests.post(
            f"{self.base_url}/infer/batch",
            headers=self.headers,
            json={"texts": texts, "use_cloud_inference": use_cloud}
        )
        return response.json()

# 使用示例
client = PulseWeaveClient()
result = client.infer("明天开会记得带资料")
print(result)
```

### JavaScript客户端

```javascript
class PulseWeaveClient {
    constructor(baseUrl = 'http://localhost:8000', token = null) {
        this.baseUrl = baseUrl;
        this.headers = {'Content-Type': 'application/json'};
        if (token) {
            this.headers['Authorization'] = `Bearer ${token}`;
        }
    }
    
    async infer(text, useCloud = false) {
        const endpoint = useCloud ? '/infer/cloud' : '/infer';
        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify({text})
        });
        return response.json();
    }
}

// 使用示例
const client = new PulseWeaveClient();
client.infer('明天开会记得带资料').then(result => {
    console.log(result);
});
```

## 📚 更多资源

- **API对接协议**: [API_PROTOCOL.md](API_PROTOCOL.md) - **Web端对接必读**
- **详细使用文档**: [API_USAGE.md](API_USAGE.md)
- **工作流程详解**: [WORKFLOW.md](WORKFLOW.md)
- **项目结构说明**: [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)
- **完整README**: [README.md](README.md)
- **API文档**: http://localhost:8000/docs

---

🎉 **恭喜！** 你已经成功启动了PulseWeave API Gateway！

现在可以开始体验智能推理服务了。如有问题，请查看故障排除部分或运行测试工具进行诊断。
