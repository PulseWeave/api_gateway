"""
ASR队列管理器 - 集成ASR转写结果到API Gateway
"""
import asyncio
import json
import os
import time
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
import logging

try:
    from asr_result_receiver_sdk import create_asr_receiver
except ImportError:
    # 如果SDK不可用，创建一个模拟版本
    print("⚠️ ASR SDK不可用，使用模拟模式")
    create_asr_receiver = None

logger = logging.getLogger(__name__)


class ASRQueueManager:
    """ASR队列管理器"""
    
    def __init__(self, queue_dir: str = "outputs", provider=None, config: Dict[str, Any] = None):
        self.queue_dir = queue_dir
        self.provider = provider  # 推理提供商
        self.receiver = None
        self.is_running = False
        self.callbacks: List[Callable] = []
        self.processed_results: List[Dict[str, Any]] = []
        
        # 从配置文件读取设置
        asr_config = config.get("asr", {}) if config else {}
        self.max_history = asr_config.get("max_history", 100)
        self.monitor_interval = asr_config.get("monitor_interval", 1.0)
        self.auto_start = asr_config.get("auto_start", True)
        
    async def initialize(self):
        """初始化ASR接收器"""
        try:
            if create_asr_receiver is None:
                logger.warning("ASR SDK不可用，使用文件监控模式")
                return
                
            self.receiver = create_asr_receiver(
                backend="file",
                queue_dir=self.queue_dir
            )
            
            # 添加处理回调
            self.receiver.add_callback(self._process_asr_result)
            logger.info(f"ASR队列管理器初始化完成，监控目录: {self.queue_dir}")
            
        except Exception as e:
            logger.error(f"ASR队列管理器初始化失败: {e}")
            
    def add_callback(self, callback: Callable):
        """添加结果处理回调"""
        self.callbacks.append(callback)
        
    async def start_listening(self):
        """开始监听ASR队列"""
        if self.is_running:
            return
            
        self.is_running = True
        logger.info("开始监听ASR转写结果...")
        
        if self.receiver:
            # 使用SDK监听（异步启动，不阻塞）
            try:
                asyncio.create_task(self._async_sdk_listening())
            except Exception as e:
                logger.error(f"SDK监听失败: {e}")
        else:
            # 使用文件监控（异步启动，不阻塞）
            asyncio.create_task(self._start_file_monitoring())
    
    async def _async_sdk_listening(self):
        """异步SDK监听"""
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, self._start_sdk_listening
            )
        except Exception as e:
            logger.error(f"异步SDK监听失败: {e}")
            
    def _start_sdk_listening(self):
        """启动SDK监听（在线程池中运行）"""
        try:
            self.receiver.start_listening(interval=self.monitor_interval)
        except Exception as e:
            logger.error(f"SDK监听异常: {e}")
            
    async def _start_file_monitoring(self):
        """文件监控模式（备用方案）"""
        logger.info("使用文件监控模式监听ASR结果")
        
        if not os.path.exists(self.queue_dir):
            os.makedirs(self.queue_dir, exist_ok=True)
            
        processed_files = set()
        
        while self.is_running:
            try:
                # 扫描outputs目录
                for filename in os.listdir(self.queue_dir):
                    if filename.endswith('.json') and filename not in processed_files:
                        file_path = os.path.join(self.queue_dir, filename)
                        
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                result_data = json.load(f)
                                
                            # 处理结果
                            await self._process_asr_result(result_data)
                            processed_files.add(filename)
                            
                        except Exception as e:
                            logger.error(f"处理文件 {filename} 失败: {e}")
                            
                await asyncio.sleep(self.monitor_interval)  # 每秒检查一次
                
            except asyncio.CancelledError:
                logger.info("文件监控被取消")
                break
            except Exception as e:
                logger.error(f"文件监控异常: {e}")
                await asyncio.sleep(5.0)
                
    async def _process_asr_result(self, result_data: Dict[str, Any]):
        """处理ASR转写结果"""
        try:
            logger.info(f"收到ASR转写结果: {result_data.get('filename', 'unknown')}")
            
            # 提取转写文本
            content = result_data.get('content', '')
            if not content.strip():
                logger.warning("ASR结果为空，跳过处理")
                return
                
            # 构建事件数据
            event_data = self._build_event_data(result_data)
            
            # 调用推理服务
            inference_result = None
            if self.provider:
                try:
                    inference_result = await self.provider.predict(content, event_data)
                    logger.info("推理分析完成")
                except Exception as e:
                    logger.error(f"推理分析失败: {e}")
                    
            # 构建完整结果
            processed_result = {
                'timestamp': datetime.now().isoformat(),
                'asr_result': result_data,
                'inference_result': inference_result,
                'event_data': event_data,
                'content': content
            }
            
            # 保存到历史记录
            self.processed_results.append(processed_result)
            if len(self.processed_results) > self.max_history:
                self.processed_results.pop(0)
                
            # 调用回调函数
            for callback in self.callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(processed_result)
                    else:
                        callback(processed_result)
                except Exception as e:
                    logger.error(f"回调函数执行失败: {e}")
                    
        except Exception as e:
            logger.error(f"处理ASR结果失败: {e}")
            
    def _build_event_data(self, result_data: Dict[str, Any]) -> Dict[str, Any]:
        """根据ASR结果构建事件数据"""
        filename = result_data.get('filename', '')
        stream_id = result_data.get('stream_id', '')
        
        # 从文件名提取时间戳
        timestamp = None
        if '_' in filename:
            timestamp_str = filename.split('_')[0]
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('T', ' '))
            except:
                pass
                
        event_data = {
            'event_id': f"asr_{stream_id}_{int(time.time())}",
            'transcript': result_data.get('content', ''),
            'source': 'asr_queue',
            'stream_id': stream_id,
            'filename': filename,
            'reason': result_data.get('reason', 'unknown'),
            'force': result_data.get('force', False),
            'timestamp': timestamp.isoformat() if timestamp else datetime.now().isoformat(),
            'audio_features': {
                'source_type': 'file_queue',
                'stream_id': stream_id
            }
        }
        
        return event_data
        
    async def stop_listening(self):
        """停止监听"""
        self.is_running = False
        if self.receiver:
            try:
                self.receiver.close()
            except Exception as e:
                logger.error(f"关闭ASR接收器失败: {e}")
        logger.info("ASR队列监听已停止")
        
    def get_recent_results(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近的处理结果"""
        return self.processed_results[-limit:] if self.processed_results else []
        
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'is_running': self.is_running,
            'queue_dir': self.queue_dir,
            'total_processed': len(self.processed_results),
            'has_sdk': create_asr_receiver is not None,
            'callbacks_count': len(self.callbacks)
        }


# 全局ASR队列管理器实例
asr_queue_manager: Optional[ASRQueueManager] = None


async def initialize_asr_queue_manager(queue_dir: str = "outputs", provider=None, config: Dict[str, Any] = None) -> ASRQueueManager:
    """初始化全局ASR队列管理器"""
    global asr_queue_manager
    
    if asr_queue_manager is None:
        asr_queue_manager = ASRQueueManager(queue_dir, provider, config)
        await asr_queue_manager.initialize()
        
        # 如果配置了自动启动，则启动监听
        if asr_queue_manager.auto_start:
            logger.info("配置了自动启动ASR队列监听")
            await asr_queue_manager.start_listening()
        
    return asr_queue_manager


def get_asr_queue_manager() -> Optional[ASRQueueManager]:
    """获取全局ASR队列管理器"""
    return asr_queue_manager
