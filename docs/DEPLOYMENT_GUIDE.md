# ASR队列集成部署指南

## 🎯 路径配置关键点

### 1. **核心路径配置位置**

#### **配置文件** (`config.yaml`)
```yaml
asr:
  # 🔑 关键：必须与同事的ASR输出目录完全一致
  queue_dir: "outputs"
  
  # 服务器部署时使用绝对路径
  # queue_dir: "/shared/asr/outputs"
```

#### **环境变量配置**（推荐用于生产环境）
```bash
# 设置ASR队列目录
export ASR_QUEUE_DIR="/path/to/shared/outputs"

# 或在.env文件中
ASR_QUEUE_DIR=/path/to/shared/outputs
```

### 2. **部署场景路径配置**

#### **场景A：同一服务器部署**
```yaml
# 同事的ASR系统和API Gateway在同一台服务器
asr:
  queue_dir: "/home/asr/outputs"  # 绝对路径
```

#### **场景B：共享存储部署**
```yaml
# 通过NFS或其他共享存储
asr:
  queue_dir: "/mnt/shared/asr_outputs"  # 共享存储路径
```

#### **场景C：相对路径部署**
```yaml
# API Gateway与ASR系统在相邻目录
asr:
  queue_dir: "../asr_system/outputs"  # 相对路径
```

### 3. **代码中的路径处理逻辑**

#### **ASR队列管理器初始化**
```python
# asr_queue_manager.py 第25行
def __init__(self, queue_dir: str = "outputs", provider=None, config: Dict[str, Any] = None):
    # 支持环境变量覆盖
    self.queue_dir = os.getenv("ASR_QUEUE_DIR", queue_dir)
```

#### **自动目录创建**
```python
# asr_queue_manager.py 第65行
if not os.path.exists(self.queue_dir):
    os.makedirs(self.queue_dir, exist_ok=True)  # 自动创建目录
```

## 🚀 部署步骤

### **步骤1：确认同事的ASR输出目录**
```bash
# 找到同事ASR系统的输出目录
ls -la /path/to/colleague/asr/outputs/
```

### **步骤2：配置API Gateway**
```bash
# 编辑配置文件
vim api_gateway/config.yaml

# 或设置环境变量
export ASR_QUEUE_DIR="/path/to/colleague/asr/outputs"
```

### **步骤3：验证路径权限**
```bash
# 确保API Gateway有读取权限
ls -la /path/to/colleague/asr/outputs/
chmod 755 /path/to/colleague/asr/outputs/  # 如果需要
```

### **步骤4：测试连接**
```bash
# 启动API Gateway
python start_server.py

# 检查ASR队列状态
curl http://localhost:8000/asr/stats
```

## ⚠️ 重要注意事项

### **1. 路径一致性**
- API Gateway的 `queue_dir` 必须与同事ASR系统的输出目录完全一致
- 建议使用绝对路径避免相对路径问题

### **2. 文件权限**
```bash
# 确保API Gateway进程有读取权限
chmod 755 /path/to/asr/outputs/
chmod 644 /path/to/asr/outputs/*.json
```

### **3. 文件格式**
同事的ASR系统输出格式：
- 音频文件：`时间戳_audio.wav`
- 结束消息：`时间戳_end_msg.json`

### **4. 监控和日志**
```bash
# 启用调试日志查看路径问题
python start_server.py --log-level debug
```

## 🔧 故障排除

### **问题1：找不到队列目录**
```
错误：FileNotFoundError: [Errno 2] No such file or directory: 'outputs'
解决：检查config.yaml中的queue_dir路径是否正确
```

### **问题2：权限被拒绝**
```
错误：PermissionError: [Errno 13] Permission denied
解决：chmod 755 /path/to/asr/outputs/
```

### **问题3：SDK不可用**
```
警告：ASR SDK不可用，使用文件监控模式
说明：这是正常的，系统会自动切换到文件监控模式
```

## 📊 监控接口

### **检查ASR队列状态**
```bash
curl http://localhost:8000/asr/stats
```

### **获取处理结果**
```bash
curl http://localhost:8000/asr/results?limit=5
```

### **启动/停止队列监听**
```bash
# 启动
curl -X POST http://localhost:8000/asr/start

# 停止
curl -X POST http://localhost:8000/asr/stop
```

## 🌐 生产环境建议

### **1. 使用环境变量**
```bash
# 在生产环境中设置
export ASR_QUEUE_DIR="/production/asr/outputs"
export API_CONFIG="/etc/pulseweave/config.yaml"
```

### **2. 服务化部署**
```bash
# 使用systemd管理服务
sudo systemctl start pulseweave-gateway
sudo systemctl enable pulseweave-gateway
```

### **3. 日志管理**
```bash
# 配置日志轮转
/var/log/pulseweave/*.log {
    daily
    rotate 7
    compress
}
```

这样配置后，API Gateway就能正确地从同事的ASR系统获取转写结果并进行智能分析了。
