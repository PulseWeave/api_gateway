#!/usr/bin/env python3
"""
WebSocket连接管理器
负责管理WebSocket连接、任务队列和实时通知
"""

import asyncio
import json
import uuid
import time
from typing import Dict, List, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"      # 等待处理
    PROCESSING = "processing"  # 正在处理
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"        # 失败
    CANCELLED = "cancelled"   # 已取消


class InferenceTask:
    """推理任务"""
    def __init__(self, task_id: str, client_id: str, request_data: Dict[str, Any]):
        self.task_id = task_id
        self.client_id = client_id
        self.request_data = request_data
        self.status = TaskStatus.PENDING
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.created_at = time.time()
        self.started_at: Optional[float] = None
        self.completed_at: Optional[float] = None
        
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "task_id": self.task_id,
            "client_id": self.client_id,
            "status": self.status.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "result": self.result,
            "error": self.error
        }


class WebSocketManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 活跃的WebSocket连接
        self.active_connections: Dict[str, WebSocket] = {}
        
        # 任务队列和状态
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.tasks: Dict[str, InferenceTask] = {}
        
        # 客户端订阅的任务
        self.client_subscriptions: Dict[str, List[str]] = {}
        
        # 统计信息
        self.stats = {
            "total_connections": 0,
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0
        }
        
    async def connect(self, websocket: WebSocket, client_id: str):
        """建立WebSocket连接"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.client_subscriptions[client_id] = []
        self.stats["total_connections"] += 1
        
        logger.info(f"WebSocket客户端 {client_id} 已连接")
        
        # 发送连接确认
        await self.send_to_client(client_id, {
            "type": "connection_established",
            "client_id": client_id,
            "timestamp": time.time()
        })
        
    async def disconnect(self, client_id: str):
        """断开WebSocket连接"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            
        if client_id in self.client_subscriptions:
            del self.client_subscriptions[client_id]
            
        logger.info(f"WebSocket客户端 {client_id} 已断开")
        
    async def send_to_client(self, client_id: str, message: Dict[str, Any]):
        """向指定客户端发送消息"""
        if client_id in self.active_connections:
            try:
                websocket = self.active_connections[client_id]
                await websocket.send_text(json.dumps(message, ensure_ascii=False))
            except Exception as e:
                logger.error(f"向客户端 {client_id} 发送消息失败: {e}")
                await self.disconnect(client_id)
                
    async def broadcast(self, message: Dict[str, Any]):
        """广播消息给所有连接的客户端"""
        disconnected_clients = []
        
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(json.dumps(message, ensure_ascii=False))
            except Exception as e:
                logger.error(f"向客户端 {client_id} 广播消息失败: {e}")
                disconnected_clients.append(client_id)
                
        # 清理断开的连接
        for client_id in disconnected_clients:
            await self.disconnect(client_id)
            
    async def submit_task(self, client_id: str, request_data: Dict[str, Any]) -> str:
        """提交推理任务"""
        task_id = str(uuid.uuid4())
        task = InferenceTask(task_id, client_id, request_data)
        
        self.tasks[task_id] = task
        self.client_subscriptions[client_id].append(task_id)
        self.stats["total_tasks"] += 1
        
        # 将任务加入队列
        await self.task_queue.put(task)
        
        logger.info(f"任务 {task_id} 已提交，客户端: {client_id}")
        
        # 通知客户端任务已提交
        await self.send_to_client(client_id, {
            "type": "task_submitted",
            "task_id": task_id,
            "status": TaskStatus.PENDING.value,
            "timestamp": time.time()
        })
        
        return task_id
        
    async def update_task_status(self, task_id: str, status: TaskStatus, 
                               result: Optional[Dict[str, Any]] = None,
                               error: Optional[str] = None):
        """更新任务状态"""
        if task_id not in self.tasks:
            logger.warning(f"任务 {task_id} 不存在")
            return
            
        task = self.tasks[task_id]
        task.status = status
        
        if status == TaskStatus.PROCESSING:
            task.started_at = time.time()
        elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            task.completed_at = time.time()
            
            if status == TaskStatus.COMPLETED:
                task.result = result
                self.stats["completed_tasks"] += 1
            elif status == TaskStatus.FAILED:
                task.error = error
                self.stats["failed_tasks"] += 1
                
        # 通知客户端状态更新
        message = {
            "type": "task_status_update",
            "task_id": task_id,
            "status": status.value,
            "timestamp": time.time()
        }
        
        if result:
            message["result"] = result
        if error:
            message["error"] = error
            
        await self.send_to_client(task.client_id, message)
        
        logger.info(f"任务 {task_id} 状态更新为: {status.value}")
        
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        if task_id in self.tasks:
            return self.tasks[task_id].to_dict()
        return None
        
    async def get_client_tasks(self, client_id: str) -> List[Dict[str, Any]]:
        """获取客户端的所有任务"""
        if client_id not in self.client_subscriptions:
            return []
            
        task_ids = self.client_subscriptions[client_id]
        return [self.tasks[task_id].to_dict() for task_id in task_ids if task_id in self.tasks]
        
    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        active_tasks = sum(1 for task in self.tasks.values() 
                          if task.status in [TaskStatus.PENDING, TaskStatus.PROCESSING])
        
        return {
            **self.stats,
            "active_connections": len(self.active_connections),
            "active_tasks": active_tasks,
            "queue_size": self.task_queue.qsize()
        }
        
    async def cleanup_old_tasks(self, max_age_hours: int = 24):
        """清理旧任务"""
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        old_task_ids = []
        for task_id, task in self.tasks.items():
            if (current_time - task.created_at) > max_age_seconds:
                old_task_ids.append(task_id)
                
        for task_id in old_task_ids:
            task = self.tasks[task_id]
            # 从客户端订阅中移除
            if task.client_id in self.client_subscriptions:
                if task_id in self.client_subscriptions[task.client_id]:
                    self.client_subscriptions[task.client_id].remove(task_id)
            # 删除任务
            del self.tasks[task_id]
            
        if old_task_ids:
            logger.info(f"清理了 {len(old_task_ids)} 个旧任务")


# 全局WebSocket管理器实例
websocket_manager = WebSocketManager()


async def handle_websocket_message(client_id: str, message: Dict[str, Any]):
    """处理WebSocket消息"""
    message_type = message.get("type")
    
    if message_type == "submit_task":
        # 提交推理任务
        request_data = message.get("data", {})
        task_id = await websocket_manager.submit_task(client_id, request_data)
        return {"type": "task_submitted", "task_id": task_id}
        
    elif message_type == "get_task_status":
        # 查询任务状态
        task_id = message.get("task_id")
        status = await websocket_manager.get_task_status(task_id)
        return {"type": "task_status", "task_id": task_id, "status": status}
        
    elif message_type == "get_my_tasks":
        # 获取我的任务列表
        tasks = await websocket_manager.get_client_tasks(client_id)
        return {"type": "my_tasks", "tasks": tasks}
        
    elif message_type == "get_stats":
        # 获取统计信息
        stats = await websocket_manager.get_stats()
        return {"type": "stats", "data": stats}
        
    elif message_type == "ping":
        # 心跳检测
        return {"type": "pong", "timestamp": time.time()}
        
    else:
        return {"type": "error", "message": f"未知消息类型: {message_type}"}
