# PulseWeave WebSocket 协议规范

## 🔄 协议概述

**协议名称**: PulseWeave WebSocket Real-time API v1.0  
**协议类型**: WebSocket (RFC 6455)  
**数据格式**: JSON  
**字符编码**: UTF-8  
**用途**: 异步推理任务提交和实时状态通知

## 🎯 核心优势

### 为什么使用WebSocket？
1. **异步处理**: 推理任务可能需要几秒到几十秒，HTTP同步等待不现实
2. **实时通知**: 任务状态变化时立即通知客户端
3. **双向通信**: 客户端可以随时查询状态、提交新任务
4. **连接复用**: 一个连接处理多个任务，减少开销
5. **进度跟踪**: 可以实时显示任务队列状态和处理进度

## 🌐 连接信息

### 连接地址
```
开发环境: ws://localhost:8000/ws
测试环境: wss://test-api.pulseweave.com/ws
生产环境: wss://api.pulseweave.com/ws
```

### 连接流程
1. 客户端发起WebSocket连接
2. 服务器自动分配客户端ID
3. 发送连接确认消息
4. 开始双向通信

## 📡 消息格式

### 基础消息结构
```json
{
  "type": "message_type",
  "data": {},
  "timestamp": 1704441600.123
}
```

## 📤 客户端发送消息

### 1. 提交推理任务
```json
{
  "type": "submit_task",
  "data": {
    "text": "明早七点去机场，记得身份证和充电宝"
  }
}
```

或者提交完整事件数据：
```json
{
  "type": "submit_task",
  "data": {
    "event": {
      "event_id": "evt_20250901_090005_0001",
      "transcript": "明早七点去机场，记得身份证和充电宝",
      "speakers": [...],
      "audio_features": {...}
    }
  }
}
```

### 2. 查询任务状态
```json
{
  "type": "get_task_status",
  "task_id": "task-uuid-here"
}
```

### 3. 获取我的任务列表
```json
{
  "type": "get_my_tasks"
}
```

### 4. 获取统计信息
```json
{
  "type": "get_stats"
}
```

### 5. 心跳检测
```json
{
  "type": "ping"
}
```

## 📥 服务器发送消息

### 1. 连接确认
```json
{
  "type": "connection_established",
  "client_id": "client-uuid-here",
  "timestamp": 1704441600.123
}
```

### 2. 任务提交确认
```json
{
  "type": "task_submitted",
  "task_id": "task-uuid-here",
  "status": "pending",
  "timestamp": 1704441600.123
}
```

### 3. 任务状态更新
```json
{
  "type": "task_status_update",
  "task_id": "task-uuid-here",
  "status": "processing",
  "timestamp": 1704441600.123
}
```

### 4. 任务完成通知
```json
{
  "type": "task_status_update",
  "task_id": "task-uuid-here",
  "status": "completed",
  "timestamp": 1704441600.123,
  "result": {
    "task_type": "trip",
    "confidence": 0.85,
    "potential_omissions": ["行李", "交通工具"],
    "summary_text": "很确定这是一个出行安排...",
    "suggested_plan": "建议提前一晚准备好证件和行李...",
    // 如果是事件数据，还包含增强分析结果
    "extracted_entities": [...],
    "suggested_tags": [...],
    "priority_level": "high"
  }
}
```

### 5. 任务失败通知
```json
{
  "type": "task_status_update",
  "task_id": "task-uuid-here",
  "status": "failed",
  "timestamp": 1704441600.123,
  "error": "DeepSeek API调用失败: 网络超时"
}
```

### 6. 任务列表响应
```json
{
  "type": "my_tasks",
  "tasks": [
    {
      "task_id": "task-uuid-1",
      "status": "completed",
      "created_at": 1704441600.123,
      "completed_at": 1704441605.456,
      "result": {...}
    },
    {
      "task_id": "task-uuid-2", 
      "status": "processing",
      "created_at": 1704441610.789,
      "started_at": 1704441611.123
    }
  ]
}
```

### 7. 统计信息响应
```json
{
  "type": "stats",
  "data": {
    "active_connections": 5,
    "total_tasks": 150,
    "active_tasks": 3,
    "completed_tasks": 140,
    "failed_tasks": 7,
    "queue_size": 2
  }
}
```

### 8. 心跳响应
```json
{
  "type": "pong",
  "timestamp": 1704441600.123
}
```

### 9. 错误消息
```json
{
  "type": "error",
  "message": "无效的JSON格式"
}
```

## 📊 任务状态说明

| 状态 | 说明 | 下一步 |
|------|------|--------|
| `pending` | 任务已提交，等待处理 | 进入处理队列 |
| `processing` | 正在处理中 | 等待完成或失败 |
| `completed` | 处理完成 | 可以获取结果 |
| `failed` | 处理失败 | 查看错误信息 |
| `cancelled` | 任务被取消 | 终止状态 |

## 💻 客户端集成示例

### JavaScript/TypeScript
```typescript
class PulseWeaveWebSocketClient {
    private ws: WebSocket | null = null;
    private clientId: string | null = null;
    private tasks: Map<string, any> = new Map();
    
    constructor(private url: string) {}
    
    connect(): Promise<void> {
        return new Promise((resolve, reject) => {
            this.ws = new WebSocket(this.url);
            
            this.ws.onopen = () => {
                console.log('WebSocket连接已建立');
            };
            
            this.ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleMessage(data);
                
                if (data.type === 'connection_established') {
                    this.clientId = data.client_id;
                    resolve();
                }
            };
            
            this.ws.onerror = (error) => {
                reject(error);
            };
            
            this.ws.onclose = () => {
                console.log('WebSocket连接已断开');
            };
        });
    }
    
    submitTask(text: string): Promise<string> {
        return new Promise((resolve) => {
            const message = {
                type: 'submit_task',
                data: { text }
            };
            
            this.send(message);
            
            // 监听任务提交确认
            const handler = (data: any) => {
                if (data.type === 'task_submitted') {
                    resolve(data.task_id);
                }
            };
            
            this.addMessageHandler(handler);
        });
    }
    
    onTaskUpdate(callback: (taskId: string, status: string, result?: any) => void) {
        this.addMessageHandler((data: any) => {
            if (data.type === 'task_status_update') {
                callback(data.task_id, data.status, data.result);
            }
        });
    }
    
    private send(message: any) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        }
    }
    
    private handleMessage(data: any) {
        // 处理消息的逻辑
        console.log('收到消息:', data);
    }
    
    private addMessageHandler(handler: (data: any) => void) {
        // 添加消息处理器的逻辑
    }
}

// 使用示例
const client = new PulseWeaveWebSocketClient('ws://localhost:8000/ws');

await client.connect();

// 提交任务
const taskId = await client.submitTask('明天开会记得带资料');

// 监听任务状态更新
client.onTaskUpdate((taskId, status, result) => {
    console.log(`任务 ${taskId} 状态: ${status}`);
    if (status === 'completed') {
        console.log('推理结果:', result);
    }
});
```

### Python
```python
import asyncio
import json
import websockets
from typing import Callable, Optional, Dict, Any

class PulseWeaveWebSocketClient:
    def __init__(self, url: str):
        self.url = url
        self.ws = None
        self.client_id = None
        self.message_handlers = []
        
    async def connect(self):
        """连接到WebSocket服务器"""
        self.ws = await websockets.connect(self.url)
        
        # 等待连接确认
        message = await self.ws.recv()
        data = json.loads(message)
        
        if data['type'] == 'connection_established':
            self.client_id = data['client_id']
            print(f"连接已建立，客户端ID: {self.client_id}")
            
        # 启动消息监听
        asyncio.create_task(self._listen())
        
    async def submit_task(self, text: str = None, event: Dict[str, Any] = None) -> str:
        """提交推理任务"""
        message = {
            "type": "submit_task",
            "data": {}
        }
        
        if text:
            message["data"]["text"] = text
        if event:
            message["data"]["event"] = event
            
        await self._send(message)
        
        # 等待任务提交确认
        # 这里可以实现更复杂的等待逻辑
        
    async def get_stats(self):
        """获取统计信息"""
        await self._send({"type": "get_stats"})
        
    async def ping(self):
        """发送心跳"""
        await self._send({"type": "ping"})
        
    def on_task_update(self, callback: Callable):
        """注册任务状态更新回调"""
        self.message_handlers.append(callback)
        
    async def _send(self, message: Dict[str, Any]):
        """发送消息"""
        if self.ws:
            await self.ws.send(json.dumps(message))
            
    async def _listen(self):
        """监听消息"""
        async for message in self.ws:
            data = json.loads(message)
            
            # 调用所有消息处理器
            for handler in self.message_handlers:
                try:
                    await handler(data)
                except Exception as e:
                    print(f"消息处理器错误: {e}")
                    
    async def close(self):
        """关闭连接"""
        if self.ws:
            await self.ws.close()

# 使用示例
async def main():
    client = PulseWeaveWebSocketClient('ws://localhost:8000/ws')
    
    # 注册任务状态更新处理器
    async def on_task_update(data):
        if data['type'] == 'task_status_update':
            print(f"任务 {data['task_id']} 状态: {data['status']}")
            if data['status'] == 'completed':
                print(f"推理结果: {data['result']}")
                
    client.on_task_update(on_task_update)
    
    # 连接并提交任务
    await client.connect()
    await client.submit_task("明天开会记得带资料")
    
    # 保持连接
    await asyncio.sleep(30)
    await client.close()

# 运行
asyncio.run(main())
```

## 🔧 最佳实践

### 1. 连接管理
- 实现自动重连机制
- 处理网络中断情况
- 设置合理的心跳间隔

### 2. 错误处理
- 捕获JSON解析错误
- 处理连接异常
- 实现任务超时机制

### 3. 性能优化
- 避免频繁提交任务
- 合理设置消息缓冲
- 及时清理已完成的任务

### 4. 安全考虑
- 验证消息格式
- 限制任务提交频率
- 保护敏感信息

## 🚀 与HTTP API的对比

| 特性 | HTTP API | WebSocket API |
|------|----------|---------------|
| 通信方式 | 请求-响应 | 双向实时 |
| 适用场景 | 快速查询 | 长时间推理 |
| 连接开销 | 每次请求建连 | 一次建连复用 |
| 状态通知 | 需要轮询 | 实时推送 |
| 实现复杂度 | 简单 | 中等 |
| 网络效率 | 较低 | 高 |

## 📋 集成建议

### 推荐使用场景
1. **批量推理**: 需要处理多个任务时
2. **实时应用**: 需要立即获得结果通知
3. **长时间任务**: 推理时间超过10秒的场景
4. **进度跟踪**: 需要显示处理进度的应用

### 保留HTTP API的场景
1. **简单集成**: 快速原型或简单应用
2. **单次查询**: 偶尔使用的功能
3. **RESTful风格**: 需要符合REST规范的系统
4. **缓存友好**: 需要HTTP缓存的场景

---

**协议版本**: v1.0  
**最后更新**: 2025-01-05  
**维护团队**: PulseWeave开发团队
