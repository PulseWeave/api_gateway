#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PulseWeave API Gateway 启动脚本
提供便捷的服务启动和配置选项
"""

import os
import sys
import argparse
import subprocess
import yaml
import signal
from pathlib import Path

# 设置输出编码
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())


def check_dependencies():
    """检查依赖是否安装"""
    try:
        import fastapi
        import uvicorn
        import httpx
        import tenacity
        import pydantic
        print("✅ 核心依赖检查通过")
        return True
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        print("请运行: pip install -r requirements.txt")
        return False


def check_config(config_path: str):
    """检查配置文件"""
    if not os.path.exists(config_path):
        print(f"❌ 配置文件不存在: {config_path}")
        
        # 检查是否有示例配置
        example_path = config_path.replace('.yaml', '.example.yaml')
        if os.path.exists(example_path):
            print(f"💡 发现示例配置: {example_path}")
            if input("是否复制示例配置? (y/N): ").lower() == 'y':
                import shutil
                shutil.copy(example_path, config_path)
                print(f"✅ 已复制配置文件到: {config_path}")
                print("⚠️  请编辑配置文件设置API密钥等信息")
                return True
        return False
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 检查必要配置
        if not config:
            print("❌ 配置文件为空")
            return False
        
        provider_config = config.get('provider', {})
        if not provider_config:
            print("❌ 缺少provider配置")
            return False
        
        provider_name = provider_config.get('name')
        if not provider_name:
            print("❌ 缺少provider.name配置")
            return False
        
        # 检查API密钥
        api_key = provider_config.get('api_key')
        env_key = None
        
        if provider_name == 'deepseek':
            env_key = os.getenv('DEEPSEEK_API_KEY')
        elif provider_name == 'openai':
            env_key = os.getenv('OPENAI_API_KEY')
        
        if not api_key and not env_key and provider_name != 'dummy':
            print(f"⚠️  未配置API密钥，请设置环境变量或在配置文件中设置")
            print(f"   环境变量: {provider_name.upper()}_API_KEY")
            print(f"   配置文件: provider.api_key")
        
        print("✅ 配置文件检查通过")
        return True
        
    except Exception as e:
        print(f"❌ 配置文件解析失败: {e}")
        return False


def setup_environment():
    """设置环境"""
    # 添加当前目录和项目根目录到Python路径
    current_dir = Path(__file__).parent
    project_root = current_dir.parent

    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # 设置环境变量
    pythonpath = os.environ.get('PYTHONPATH', '')
    paths_to_add = [str(current_dir), str(project_root)]
    for path in paths_to_add:
        if path not in pythonpath:
            pythonpath = f"{path}{os.pathsep}{pythonpath}" if pythonpath else path
    os.environ['PYTHONPATH'] = pythonpath


def start_server(host: str, port: int, reload: bool, workers: int, log_level: str):
    """启动服务器"""
    cmd = [
        'uvicorn', 
        'server:app',
        '--host', host,
        '--port', str(port),
        '--log-level', log_level
    ]
    
    if reload:
        cmd.append('--reload')
    elif workers > 1:
        cmd.extend(['--workers', str(workers)])
    
    print(f"🚀 启动服务器...")
    print(f"📍 地址: http://{host}:{port}")
    print(f"📚 API文档: http://{host}:{port}/docs")
    print(f"🎨 演示界面: http://{host}:{port}/ui/")
    print(f"🔧 高级界面: http://{host}:{port}/ui/advanced_demo.html")
    print("-" * 60)
    print("💡 按 Ctrl+C 停止服务器")
    
    try:
        # 使用Popen以便更好地处理信号
        process = subprocess.Popen(cmd)
        process.wait()
    except KeyboardInterrupt:
        print("\n⏹️ 正在停止服务器...")
        try:
            process.terminate()
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print("⚠️ 强制终止服务器...")
            process.kill()
        print("👋 服务器已停止")
    except subprocess.CalledProcessError as e:
        print(f"❌ 服务器启动失败: {e}")
        sys.exit(1)


def run_tests(base_url: str, auth_token: str = None):
    """运行测试"""
    print("🧪 运行API测试...")
    
    cmd = ['python', 'test_api.py', '--url', base_url]
    if auth_token:
        cmd.extend(['--token', auth_token])
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ 测试失败: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="PulseWeave API Gateway 启动脚本")
    
    # 服务器选项
    parser.add_argument('--host', default='0.0.0.0', help='绑定主机地址')
    parser.add_argument('--port', type=int, default=8000, help='端口号')
    parser.add_argument('--reload', action='store_true', help='启用自动重载（开发模式）')
    parser.add_argument('--workers', type=int, default=1, help='工作进程数（生产模式）')
    parser.add_argument('--log-level', default='info', 
                       choices=['critical', 'error', 'warning', 'info', 'debug'],
                       help='日志级别')
    
    # 配置选项
    parser.add_argument('--config', default='config.yaml', help='配置文件路径')
    parser.add_argument('--check-only', action='store_true', help='只检查配置，不启动服务')
    
    # 测试选项
    parser.add_argument('--test', action='store_true', help='运行测试后退出')
    parser.add_argument('--test-url', default='http://localhost:8000', help='测试服务地址')
    parser.add_argument('--test-token', help='测试认证Token')
    
    # 其他选项
    parser.add_argument('--install-deps', action='store_true', help='安装依赖包')
    
    args = parser.parse_args()
    
    print("🌊 PulseWeave API Gateway 启动器")
    print("=" * 50)
    
    # 安装依赖
    if args.install_deps:
        print("📦 安装依赖包...")
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                         check=True)
            print("✅ 依赖安装完成")
        except subprocess.CalledProcessError as e:
            print(f"❌ 依赖安装失败: {e}")
            sys.exit(1)
    
    # 设置环境
    setup_environment()
    
    # 检查依赖
    if not check_dependencies():
        print("💡 尝试运行: python start_server.py --install-deps")
        sys.exit(1)
    
    # 检查配置
    config_path = args.config
    if not os.path.isabs(config_path):
        config_path = os.path.join(os.path.dirname(__file__), config_path)
    
    if not check_config(config_path):
        sys.exit(1)
    
    # 设置配置文件环境变量
    os.environ['API_CONFIG'] = config_path
    
    if args.check_only:
        print("✅ 所有检查通过，服务可以启动")
        return
    
    # 运行测试
    if args.test:
        run_tests(args.test_url, args.test_token)
        return
    
    # 启动服务器
    start_server(args.host, args.port, args.reload, args.workers, args.log_level)


if __name__ == "__main__":
    main()
