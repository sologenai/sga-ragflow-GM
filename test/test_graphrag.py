#!/usr/bin/env python3
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

import pytest
import asyncio
import json
import networkx as nx
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

# Import GraphRAG modules
from graphrag.config_manager import GraphRAGConfig, GraphRAGConfigManager, create_graphrag_task
from graphrag.task_monitor import GraphRAGTaskMonitor, TaskStatus, TaskProgress
from graphrag.general.index import run_graphrag, generate_subgraph, merge_subgraph
from graphrag.utils import GraphChange


class TestGraphRAGConfig:
    """Test GraphRAG configuration management."""
    
    def test_default_config(self):
        """Test default configuration creation."""
        config = GraphRAGConfig()
        assert config.use_graphrag is False
        assert config.method == "light"
        assert config.entity_types == ["organization", "person", "geo", "event", "category"]
        assert config.resolution is False
        assert config.community is False
    
    def test_config_validation(self):
        """Test configuration validation."""
        # Valid configuration
        config = GraphRAGConfig(
            use_graphrag=True,
            method="general",
            entity_types=["person", "organization"],
            resolution=True,
            community=True
        )
        config.validate()  # Should not raise
        
        # Invalid method
        with pytest.raises(ValueError, match="Invalid method"):
            GraphRAGConfig(method="invalid")
        
        # Empty entity types
        with pytest.raises(ValueError, match="entity_types must be a non-empty list"):
            GraphRAGConfig(entity_types=[])
    
    def test_config_serialization(self):
        """Test configuration serialization and deserialization."""
        original_config = GraphRAGConfig(
            use_graphrag=True,
            method="general",
            entity_types=["person", "organization"],
            resolution=True,
            community=True
        )
        
        # Serialize to dict
        config_dict = original_config.to_dict()
        assert isinstance(config_dict, dict)
        assert config_dict["use_graphrag"] is True
        assert config_dict["method"] == "general"
        
        # Deserialize from dict
        restored_config = GraphRAGConfig.from_dict(config_dict)
        assert restored_config.use_graphrag == original_config.use_graphrag
        assert restored_config.method == original_config.method
        assert restored_config.entity_types == original_config.entity_types


class TestGraphRAGConfigManager:
    """Test GraphRAG configuration manager."""
    
    def test_validate_task_config(self):
        """Test task configuration validation."""
        # Valid task with GraphRAG enabled
        task = {
            "tenant_id": "test_tenant",
            "kb_id": "test_kb",
            "doc_id": "test_doc",
            "kb_parser_config": {
                "graphrag": {
                    "use_graphrag": True,
                    "method": "light",
                    "entity_types": ["person", "organization"],
                    "resolution": False,
                    "community": True
                }
            }
        }
        
        config = GraphRAGConfigManager.validate_task_config(task)
        assert config.use_graphrag is True
        assert config.method == "light"
        assert config.entity_types == ["person", "organization"]
        
        # Task without GraphRAG config
        task_no_graphrag = {
            "tenant_id": "test_tenant",
            "kb_id": "test_kb",
            "doc_id": "test_doc",
            "kb_parser_config": {}
        }
        
        config = GraphRAGConfigManager.validate_task_config(task_no_graphrag)
        assert config.use_graphrag is False
    
    def test_estimate_processing_time(self):
        """Test processing time estimation."""
        config = GraphRAGConfig(use_graphrag=True, method="light")
        time_estimate = GraphRAGConfigManager.estimate_processing_time(config, 10)
        assert time_estimate >= 60  # Minimum 1 minute
        
        # Disabled GraphRAG should return 0
        config_disabled = GraphRAGConfig(use_graphrag=False)
        time_estimate = GraphRAGConfigManager.estimate_processing_time(config_disabled, 10)
        assert time_estimate == 0
    
    def test_validate_entity_types(self):
        """Test entity types validation."""
        # Valid entity types
        valid_types = ["person", "organization", "location"]
        result = GraphRAGConfigManager.validate_entity_types(valid_types)
        assert result == ["person", "organization", "location"]
        
        # Empty list should return defaults
        result = GraphRAGConfigManager.validate_entity_types([])
        assert result == GraphRAGConfigManager.DEFAULT_ENTITY_TYPES
        
        # None should return defaults
        result = GraphRAGConfigManager.validate_entity_types(None)
        assert result == GraphRAGConfigManager.DEFAULT_ENTITY_TYPES


class TestGraphRAGTaskMonitor:
    """Test GraphRAG task monitoring."""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis connection."""
        return Mock()
    
    @pytest.fixture
    def task_monitor(self, mock_redis):
        """Create task monitor with mocked Redis."""
        return GraphRAGTaskMonitor(redis_conn=mock_redis)
    
    def test_create_task_progress(self, task_monitor, mock_redis):
        """Test task progress creation."""
        progress = task_monitor.create_task_progress(
            task_id="test_task",
            tenant_id="test_tenant",
            kb_id="test_kb",
            doc_id="test_doc"
        )
        
        assert progress.task_id == "test_task"
        assert progress.tenant_id == "test_tenant"
        assert progress.status == TaskStatus.PENDING
        assert progress.progress == 0.0
        assert progress.start_time is not None
        
        # Verify Redis call
        mock_redis.setex.assert_called_once()
    
    def test_update_progress(self, task_monitor, mock_redis):
        """Test progress updates."""
        # Mock existing progress
        existing_progress = TaskProgress(
            task_id="test_task",
            tenant_id="test_tenant",
            kb_id="test_kb",
            doc_id="test_doc",
            status=TaskStatus.RUNNING
        )
        
        mock_redis.get.return_value = json.dumps(existing_progress.to_dict())
        
        # Update progress
        updated = task_monitor.update_progress(
            task_id="test_task",
            progress=0.5,
            message="Processing...",
            status=TaskStatus.RUNNING
        )
        
        assert updated is not None
        assert updated.progress == 0.5
        assert updated.message == "Processing..."
        assert updated.status == TaskStatus.RUNNING
    
    def test_progress_callback(self, task_monitor, mock_redis):
        """Test progress callback function."""
        mock_redis.get.return_value = json.dumps({
            "task_id": "test_task",
            "tenant_id": "test_tenant",
            "kb_id": "test_kb",
            "doc_id": "test_doc",
            "status": "running",
            "progress": 0.0,
            "message": "",
            "start_time": "2025-01-01T00:00:00",
            "end_time": None,
            "error_message": "",
            "metrics": {}
        })
        
        callback = task_monitor.create_progress_callback("test_task")
        
        # Test normal progress update
        callback(prog=0.5, msg="Processing...")
        mock_redis.setex.assert_called()
        
        # Test error condition (negative progress)
        callback(prog=-1.0, msg="Error occurred")
        # Should call setex again for error update
        assert mock_redis.setex.call_count >= 2


class TestGraphRAGCore:
    """Test core GraphRAG functionality."""
    
    @pytest.fixture
    def mock_task(self):
        """Mock task data."""
        return {
            "tenant_id": "test_tenant",
            "kb_id": "test_kb",
            "doc_id": "test_doc",
            "kb_parser_config": {
                "graphrag": {
                    "use_graphrag": True,
                    "method": "light",
                    "entity_types": ["person", "organization"],
                    "resolution": False,
                    "community": False
                }
            }
        }
    
    @pytest.fixture
    def mock_callback(self):
        """Mock progress callback."""
        return Mock()
    
    @pytest.fixture
    def mock_models(self):
        """Mock LLM and embedding models."""
        chat_model = Mock()
        embedding_model = Mock()
        return chat_model, embedding_model
    
    @pytest.mark.asyncio
    async def test_run_graphrag_success(self, mock_task, mock_callback, mock_models):
        """Test successful GraphRAG execution."""
        chat_model, embedding_model = mock_models
        
        with patch('graphrag.general.index.settings') as mock_settings, \
             patch('graphrag.general.index.generate_subgraph') as mock_generate, \
             patch('graphrag.general.index.merge_subgraph') as mock_merge:
            
            # Mock chunk retrieval
            mock_settings.retrievaler.chunk_list.return_value = [
                {"content_with_weight": "Test content 1"},
                {"content_with_weight": "Test content 2"}
            ]
            
            # Mock subgraph generation
            mock_subgraph = nx.Graph()
            mock_subgraph.add_node("TestEntity", entity_type="person", description="Test entity")
            mock_generate.return_value = mock_subgraph
            
            # Mock graph merging
            mock_merge.return_value = mock_subgraph
            
            # Run GraphRAG
            result = await run_graphrag(
                mock_task,
                "English",
                False,  # with_resolution
                False,  # with_community
                chat_model,
                embedding_model,
                mock_callback
            )
            
            assert result is True
            mock_callback.assert_called()
            mock_generate.assert_called_once()
            mock_merge.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_graphrag_invalid_input(self, mock_callback, mock_models):
        """Test GraphRAG with invalid input."""
        chat_model, embedding_model = mock_models
        
        # Test with None task
        result = await run_graphrag(
            None,
            "English",
            False,
            False,
            chat_model,
            embedding_model,
            mock_callback
        )
        
        assert result is False
        
        # Test with missing required fields
        invalid_task = {"tenant_id": "test"}
        result = await run_graphrag(
            invalid_task,
            "English",
            False,
            False,
            chat_model,
            embedding_model,
            mock_callback
        )
        
        assert result is False


def test_create_graphrag_task():
    """Test GraphRAG task creation."""
    config = GraphRAGConfig(
        use_graphrag=True,
        method="general",
        entity_types=["person", "organization"],
        resolution=True,
        community=True
    )
    
    task = create_graphrag_task(
        tenant_id="test_tenant",
        kb_id="test_kb",
        doc_id="test_doc",
        config=config,
        language="English",
        llm_id="test_llm"
    )
    
    assert task["tenant_id"] == "test_tenant"
    assert task["kb_id"] == "test_kb"
    assert task["doc_id"] == "test_doc"
    assert task["task_type"] == "graphrag"
    assert task["language"] == "English"
    assert task["llm_id"] == "test_llm"
    assert task["kb_parser_config"]["graphrag"]["use_graphrag"] is True
    assert task["kb_parser_config"]["graphrag"]["method"] == "general"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
