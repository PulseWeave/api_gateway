#!/usr/bin/env python3
"""
异步任务处理器
负责从队列中取出任务并执行推理
"""

import asyncio
import logging
from typing import Dict, Any
from websocket_manager import websocket_manager, TaskStatus, InferenceTask

logger = logging.getLogger(__name__)


class TaskProcessor:
    """异步任务处理器"""
    
    def __init__(self, provider, max_workers: int = 3):
        self.provider = provider
        self.max_workers = max_workers
        self.workers: list[asyncio.Task] = []
        self.running = False
        
    async def start(self):
        """启动任务处理器"""
        if self.running:
            return
            
        self.running = True
        logger.info(f"启动任务处理器，工作线程数: {self.max_workers}")
        
        # 启动工作线程
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self.workers.append(worker)
            
        # 启动清理任务
        cleanup_task = asyncio.create_task(self._cleanup_worker())
        self.workers.append(cleanup_task)
        
    async def stop(self):
        """停止任务处理器"""
        if not self.running:
            return
            
        self.running = False
        logger.info("停止任务处理器")
        
        # 取消所有工作线程
        for worker in self.workers:
            worker.cancel()
            
        # 等待所有工作线程结束
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()
        
    async def _worker(self, worker_name: str):
        """工作线程"""
        logger.info(f"工作线程 {worker_name} 已启动")
        
        while self.running:
            try:
                # 从队列中获取任务（超时1秒）
                task = await asyncio.wait_for(
                    websocket_manager.task_queue.get(), 
                    timeout=1.0
                )
                
                logger.info(f"工作线程 {worker_name} 开始处理任务 {task.task_id}")
                
                # 更新任务状态为处理中
                await websocket_manager.update_task_status(
                    task.task_id, 
                    TaskStatus.PROCESSING
                )
                
                # 执行推理
                try:
                    result = await self._process_task(task)
                    
                    # 更新任务状态为完成
                    await websocket_manager.update_task_status(
                        task.task_id,
                        TaskStatus.COMPLETED,
                        result=result
                    )
                    
                    logger.info(f"任务 {task.task_id} 处理完成")
                    
                except Exception as e:
                    logger.error(f"任务 {task.task_id} 处理失败: {e}")
                    
                    # 更新任务状态为失败
                    await websocket_manager.update_task_status(
                        task.task_id,
                        TaskStatus.FAILED,
                        error=str(e)
                    )
                    
                # 标记任务完成
                websocket_manager.task_queue.task_done()
                
            except asyncio.TimeoutError:
                # 队列为空，继续等待
                continue
            except asyncio.CancelledError:
                logger.info(f"工作线程 {worker_name} 被取消")
                break
            except Exception as e:
                logger.error(f"工作线程 {worker_name} 发生异常: {e}")
                await asyncio.sleep(1)  # 避免快速重试
                
        logger.info(f"工作线程 {worker_name} 已停止")
        
    async def _process_task(self, task: InferenceTask) -> Dict[str, Any]:
        """处理单个推理任务"""
        request_data = task.request_data
        
        # 提取文本和事件数据
        text = request_data.get("text")
        event_data = request_data.get("event")
        
        # 调用推理服务
        if text or (event_data and event_data.get("transcript")):
            result = await self.provider.predict(text, event_data)
            
            # 如果有事件数据，进行增强分析
            if event_data:
                result = await self._enhance_with_event_analysis(result, event_data)
                
            return result
        else:
            raise ValueError("必须提供 text 字段或 event.transcript 字段")
            
    async def _enhance_with_event_analysis(self, result: Dict[str, Any], event_data: Dict[str, Any]) -> Dict[str, Any]:
        """基于事件数据增强分析结果"""
        
        # 提取实体
        extracted_entities = []
        if event_data.get("entities"):
            for entity in event_data["entities"]:
                extracted_entities.append({
                    "type": entity.get("type", "unknown"),
                    "value": entity.get("value", ""),
                    "confidence": entity.get("confidence", 0.0)
                })
        
        # 建议标签
        suggested_tags = []
        if event_data.get("tags"):
            suggested_tags.extend(event_data["tags"])
        
        # 基于任务类型添加标签
        task_type = result.get("task_type", "other")
        if task_type not in suggested_tags:
            suggested_tags.append(task_type)
        
        # 优先级评估
        priority_level = "medium"  # 默认中等优先级
        confidence = result.get("confidence", 0.0)
        if confidence > 0.8:
            priority_level = "high"
        elif confidence < 0.4:
            priority_level = "low"
        
        # 提醒建议
        reminder_suggestions = []
        omissions = result.get("potential_omissions", [])
        for omission in omissions:
            reminder_suggestions.append(f"记得确认{omission}")
        
        # 事件分析
        event_analysis = {
            "has_speakers": len(event_data.get("speakers", [])) > 0,
            "speaker_count": len(event_data.get("speakers", [])),
            "has_audio_features": event_data.get("audio_features") is not None,
            "contains_pii": event_data.get("privacy", {}).get("contains_pii", False),
            "event_duration_sec": event_data.get("end_offset_sec", 0) - event_data.get("start_offset_sec", 0)
        }
        
        # 说话人洞察
        speaker_insights = None
        speakers = event_data.get("speakers", [])
        if speakers:
            user_speakers = [s for s in speakers if s.get("is_user", False)]
            speaker_insights = {
                "total_speakers": len(speakers),
                "user_speakers": len(user_speakers),
                "multi_speaker": len(speakers) > 1,
                "primary_speaker": speakers[0].get("speaker_label", "unknown") if speakers else None
            }
        
        # 音频质量评估
        audio_quality_assessment = None
        audio_features = event_data.get("audio_features")
        if audio_features:
            asr_confidence = audio_features.get("asr_confidence")
            snr_db = audio_features.get("snr_db")
            
            quality = "good"
            if asr_confidence and asr_confidence < 0.7:
                quality = "poor"
            elif snr_db and snr_db < 10:
                quality = "poor"
            elif asr_confidence and asr_confidence < 0.85:
                quality = "fair"
            
            audio_quality_assessment = {
                "overall_quality": quality,
                "asr_confidence": asr_confidence,
                "snr_db": snr_db,
                "language": audio_features.get("language"),
                "speech_rate_wpm": audio_features.get("speech_rate_wpm")
            }
        
        # 增强NLU结果
        enhanced_nlu = None
        if event_data.get("nlu"):
            enhanced_nlu = {
                "intents": event_data["nlu"].get("intents", []),
                "summary": event_data["nlu"].get("summary") or result.get("summary_text", "")
            }
        
        # 更新结果
        result.update({
            "extracted_entities": extracted_entities,
            "suggested_tags": suggested_tags,
            "priority_level": priority_level,
            "reminder_suggestions": reminder_suggestions,
            "event_analysis": event_analysis,
            "speaker_insights": speaker_insights,
            "audio_quality_assessment": audio_quality_assessment,
            "enhanced_nlu": enhanced_nlu
        })
        
        return result
        
    async def _cleanup_worker(self):
        """清理工作线程"""
        logger.info("清理工作线程已启动")
        
        while self.running:
            try:
                # 每小时清理一次旧任务
                await asyncio.sleep(3600)
                await websocket_manager.cleanup_old_tasks(max_age_hours=24)
                
            except asyncio.CancelledError:
                logger.info("清理工作线程被取消")
                break
            except Exception as e:
                logger.error(f"清理工作线程发生异常: {e}")
                await asyncio.sleep(60)  # 出错后等待1分钟再重试
                
        logger.info("清理工作线程已停止")


# 全局任务处理器实例
task_processor: TaskProcessor = None


async def start_task_processor(provider, max_workers: int = 3):
    """启动任务处理器"""
    global task_processor
    
    if task_processor is None:
        task_processor = TaskProcessor(provider, max_workers)
        await task_processor.start()
        logger.info("任务处理器已启动")
    else:
        logger.warning("任务处理器已经在运行")


async def stop_task_processor():
    """停止任务处理器"""
    global task_processor
    
    if task_processor is not None:
        await task_processor.stop()
        task_processor = None
        logger.info("任务处理器已停止")
    else:
        logger.warning("任务处理器未运行")
