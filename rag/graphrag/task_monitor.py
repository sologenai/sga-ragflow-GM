#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from rag.utils.redis_conn import REDIS_CONN


class TaskStatus(Enum):
    """GraphRAG task status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskProgress:
    """GraphRAG task progress tracking."""
    task_id: str
    tenant_id: str
    kb_id: str
    doc_id: str
    status: TaskStatus
    progress: float = 0.0
    message: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: str = ""
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "tenant_id": self.tenant_id,
            "kb_id": self.kb_id,
            "doc_id": self.doc_id,
            "status": self.status.value,
            "progress": self.progress,
            "message": self.message,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "error_message": self.error_message,
            "metrics": self.metrics,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskProgress":
        """Create from dictionary."""
        return cls(
            task_id=data["task_id"],
            tenant_id=data["tenant_id"],
            kb_id=data["kb_id"],
            doc_id=data["doc_id"],
            status=TaskStatus(data["status"]),
            progress=data.get("progress", 0.0),
            message=data.get("message", ""),
            start_time=datetime.fromisoformat(data["start_time"]) if data.get("start_time") else None,
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
            error_message=data.get("error_message", ""),
            metrics=data.get("metrics", {}),
        )


class GraphRAGTaskMonitor:
    """Monitor and manage GraphRAG task execution."""
    
    def __init__(self, redis_conn=None):
        """Initialize task monitor."""
        self.redis_conn = redis_conn or REDIS_CONN
        self.task_prefix = "graphrag:task:"
        self.progress_prefix = "graphrag:progress:"
        self.metrics_prefix = "graphrag:metrics:"
        
    def _get_task_key(self, task_id: str) -> str:
        """Get Redis key for task."""
        return f"{self.task_prefix}{task_id}"
    
    def _get_progress_key(self, task_id: str) -> str:
        """Get Redis key for task progress."""
        return f"{self.progress_prefix}{task_id}"
    
    def _get_metrics_key(self, task_id: str) -> str:
        """Get Redis key for task metrics."""
        return f"{self.metrics_prefix}{task_id}"
    
    def create_task_progress(
        self,
        task_id: str,
        tenant_id: str,
        kb_id: str,
        doc_id: str
    ) -> TaskProgress:
        """Create and store initial task progress."""
        progress = TaskProgress(
            task_id=task_id,
            tenant_id=tenant_id,
            kb_id=kb_id,
            doc_id=doc_id,
            status=TaskStatus.PENDING,
            start_time=datetime.now()
        )
        
        self._store_progress(progress)
        return progress
    
    def _store_progress(self, progress: TaskProgress) -> None:
        """Store task progress in Redis."""
        try:
            key = self._get_progress_key(progress.task_id)
            data = json.dumps(progress.to_dict())
            self.redis_conn.setex(key, 86400, data)  # 24 hours TTL
        except Exception as e:
            logging.error(f"Failed to store task progress: {e}")
    
    def update_progress(
        self,
        task_id: str,
        progress: float = None,
        message: str = None,
        status: TaskStatus = None,
        error_message: str = None,
        metrics: Dict[str, Any] = None
    ) -> Optional[TaskProgress]:
        """Update task progress."""
        try:
            current_progress = self.get_progress(task_id)
            if not current_progress:
                logging.warning(f"Task progress not found for task_id: {task_id}")
                return None
            
            # Update fields if provided
            if progress is not None:
                current_progress.progress = max(0.0, min(1.0, progress))
            if message is not None:
                current_progress.message = message
            if status is not None:
                current_progress.status = status
                if status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    current_progress.end_time = datetime.now()
            if error_message is not None:
                current_progress.error_message = error_message
            if metrics is not None:
                current_progress.metrics.update(metrics)
            
            self._store_progress(current_progress)
            return current_progress
            
        except Exception as e:
            logging.error(f"Failed to update task progress: {e}")
            return None
    
    def get_progress(self, task_id: str) -> Optional[TaskProgress]:
        """Get task progress."""
        try:
            key = self._get_progress_key(task_id)
            data = self.redis_conn.get(key)
            if not data:
                return None
            
            progress_dict = json.loads(data)
            return TaskProgress.from_dict(progress_dict)
            
        except Exception as e:
            logging.error(f"Failed to get task progress: {e}")
            return None
    
    def start_task(self, task_id: str) -> Optional[TaskProgress]:
        """Mark task as started."""
        return self.update_progress(
            task_id,
            status=TaskStatus.RUNNING,
            message="GraphRAG processing started"
        )
    
    def complete_task(self, task_id: str, metrics: Dict[str, Any] = None) -> Optional[TaskProgress]:
        """Mark task as completed."""
        return self.update_progress(
            task_id,
            progress=1.0,
            status=TaskStatus.COMPLETED,
            message="GraphRAG processing completed successfully",
            metrics=metrics or {}
        )
    
    def fail_task(self, task_id: str, error_message: str) -> Optional[TaskProgress]:
        """Mark task as failed."""
        return self.update_progress(
            task_id,
            status=TaskStatus.FAILED,
            error_message=error_message,
            message=f"GraphRAG processing failed: {error_message}"
        )
    
    def cancel_task(self, task_id: str) -> Optional[TaskProgress]:
        """Mark task as cancelled."""
        return self.update_progress(
            task_id,
            status=TaskStatus.CANCELLED,
            message="GraphRAG processing cancelled"
        )
    
    def get_tasks_by_kb(self, tenant_id: str, kb_id: str) -> List[TaskProgress]:
        """Get all tasks for a knowledge base."""
        try:
            pattern = f"{self.progress_prefix}*"
            keys = self.redis_conn.keys(pattern)
            
            tasks = []
            for key in keys:
                try:
                    data = self.redis_conn.get(key)
                    if data:
                        progress_dict = json.loads(data)
                        progress = TaskProgress.from_dict(progress_dict)
                        if progress.tenant_id == tenant_id and progress.kb_id == kb_id:
                            tasks.append(progress)
                except Exception as e:
                    logging.warning(f"Failed to parse task progress from key {key}: {e}")
                    continue
            
            # Sort by start time (newest first)
            tasks.sort(key=lambda x: x.start_time or datetime.min, reverse=True)
            return tasks
            
        except Exception as e:
            logging.error(f"Failed to get tasks by KB: {e}")
            return []
    
    def cleanup_old_tasks(self, days: int = 7) -> int:
        """Clean up old task records."""
        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            pattern = f"{self.progress_prefix}*"
            keys = self.redis_conn.keys(pattern)
            
            cleaned_count = 0
            for key in keys:
                try:
                    data = self.redis_conn.get(key)
                    if data:
                        progress_dict = json.loads(data)
                        start_time = progress_dict.get("start_time")
                        if start_time:
                            task_time = datetime.fromisoformat(start_time)
                            if task_time < cutoff_time:
                                self.redis_conn.delete(key)
                                cleaned_count += 1
                except Exception as e:
                    logging.warning(f"Failed to process cleanup for key {key}: {e}")
                    continue
            
            logging.info(f"Cleaned up {cleaned_count} old GraphRAG task records")
            return cleaned_count
            
        except Exception as e:
            logging.error(f"Failed to cleanup old tasks: {e}")
            return 0
    
    def create_progress_callback(self, task_id: str) -> Callable:
        """Create a progress callback function for task execution."""
        def callback(prog: float = None, msg: str = None):
            """Progress callback function."""
            try:
                if prog is not None and prog < 0:
                    # Negative progress indicates error
                    self.fail_task(task_id, msg or "Unknown error")
                else:
                    self.update_progress(task_id, progress=prog, message=msg)
            except Exception as e:
                logging.error(f"Progress callback error: {e}")
        
        return callback
