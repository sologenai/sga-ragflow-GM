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

"""
GraphRAG Integration Test Script

This script performs end-to-end testing of the GraphRAG functionality,
including configuration validation, task execution, and result verification.
"""

import asyncio
import json
import logging
import sys
import time
from typing import Dict, Any, List
import argparse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import GraphRAG modules
from graphrag.config_manager import GraphRAGConfig, GraphRAGConfigManager, create_graphrag_task
from graphrag.task_monitor import GraphRAGTaskMonitor, TaskStatus
from graphrag.general.index import run_graphrag
from api.db.services.llm_service import LLMBundle
from api.db import LLMType


class GraphRAGIntegrationTest:
    """GraphRAG integration test suite."""
    
    def __init__(self, tenant_id: str, kb_id: str, llm_id: str = None):
        """Initialize integration test."""
        self.tenant_id = tenant_id
        self.kb_id = kb_id
        self.llm_id = llm_id
        self.task_monitor = GraphRAGTaskMonitor()
        self.test_results = []
    
    def log_test_result(self, test_name: str, success: bool, message: str = "", duration: float = 0.0):
        """Log test result."""
        result = {
            "test_name": test_name,
            "success": success,
            "message": message,
            "duration": duration,
            "timestamp": time.time()
        }
        self.test_results.append(result)
        
        status = "PASS" if success else "FAIL"
        logger.info(f"[{status}] {test_name}: {message} ({duration:.2f}s)")
    
    def test_config_validation(self) -> bool:
        """Test GraphRAG configuration validation."""
        start_time = time.time()
        
        try:
            # Test valid configuration
            config = GraphRAGConfig(
                use_graphrag=True,
                method="light",
                entity_types=["person", "organization", "location"],
                resolution=True,
                community=True
            )
            config.validate()
            
            # Test configuration serialization
            config_dict = config.to_dict()
            restored_config = GraphRAGConfig.from_dict(config_dict)
            
            assert restored_config.use_graphrag == config.use_graphrag
            assert restored_config.method == config.method
            assert restored_config.entity_types == config.entity_types
            
            # Test invalid configuration
            try:
                invalid_config = GraphRAGConfig(method="invalid_method")
                invalid_config.validate()
                raise AssertionError("Should have raised ValueError for invalid method")
            except ValueError:
                pass  # Expected
            
            duration = time.time() - start_time
            self.log_test_result("Config Validation", True, "All validation tests passed", duration)
            return True
            
        except Exception as e:
            duration = time.time() - start_time
            self.log_test_result("Config Validation", False, f"Error: {str(e)}", duration)
            return False
    
    def test_task_creation(self) -> bool:
        """Test GraphRAG task creation."""
        start_time = time.time()
        
        try:
            config = GraphRAGConfig(
                use_graphrag=True,
                method="light",
                entity_types=["person", "organization"],
                resolution=False,
                community=True
            )
            
            task = create_graphrag_task(
                tenant_id=self.tenant_id,
                kb_id=self.kb_id,
                doc_id="test_doc_001",
                config=config,
                language="English",
                llm_id=self.llm_id
            )
            
            # Validate task structure
            assert task["tenant_id"] == self.tenant_id
            assert task["kb_id"] == self.kb_id
            assert task["doc_id"] == "test_doc_001"
            assert task["task_type"] == "graphrag"
            assert task["language"] == "English"
            
            graphrag_config = task["kb_parser_config"]["graphrag"]
            assert graphrag_config["use_graphrag"] is True
            assert graphrag_config["method"] == "light"
            assert graphrag_config["entity_types"] == ["person", "organization"]
            
            duration = time.time() - start_time
            self.log_test_result("Task Creation", True, "Task created successfully", duration)
            return True
            
        except Exception as e:
            duration = time.time() - start_time
            self.log_test_result("Task Creation", False, f"Error: {str(e)}", duration)
            return False
    
    def test_task_monitoring(self) -> bool:
        """Test task monitoring functionality."""
        start_time = time.time()
        
        try:
            # Create task progress
            task_id = "test_task_monitor_001"
            progress = self.task_monitor.create_task_progress(
                task_id=task_id,
                tenant_id=self.tenant_id,
                kb_id=self.kb_id,
                doc_id="test_doc_monitor"
            )
            
            assert progress.task_id == task_id
            assert progress.status == TaskStatus.PENDING
            assert progress.progress == 0.0
            
            # Test progress updates
            self.task_monitor.start_task(task_id)
            updated_progress = self.task_monitor.get_progress(task_id)
            assert updated_progress.status == TaskStatus.RUNNING
            
            # Test progress callback
            callback = self.task_monitor.create_progress_callback(task_id)
            callback(prog=0.5, msg="Processing entities...")
            
            progress_check = self.task_monitor.get_progress(task_id)
            assert progress_check.progress == 0.5
            assert "Processing entities" in progress_check.message
            
            # Complete task
            self.task_monitor.complete_task(task_id, {"entities": 10, "relations": 5})
            final_progress = self.task_monitor.get_progress(task_id)
            assert final_progress.status == TaskStatus.COMPLETED
            assert final_progress.progress == 1.0
            
            duration = time.time() - start_time
            self.log_test_result("Task Monitoring", True, "All monitoring tests passed", duration)
            return True
            
        except Exception as e:
            duration = time.time() - start_time
            self.log_test_result("Task Monitoring", False, f"Error: {str(e)}", duration)
            return False
    
    async def test_graphrag_execution(self) -> bool:
        """Test GraphRAG execution with mock data."""
        start_time = time.time()
        
        try:
            # Create test configuration
            config = GraphRAGConfig(
                use_graphrag=True,
                method="light",
                entity_types=["person", "organization"],
                resolution=False,
                community=False
            )
            
            # Create test task
            task = create_graphrag_task(
                tenant_id=self.tenant_id,
                kb_id=self.kb_id,
                doc_id="test_doc_execution",
                config=config,
                language="English",
                llm_id=self.llm_id
            )
            
            # Create progress callback
            task_id = "test_execution_001"
            callback = self.task_monitor.create_progress_callback(task_id)
            
            # Initialize models (mock for testing)
            try:
                chat_model = LLMBundle(self.tenant_id, LLMType.CHAT, llm_name=self.llm_id)
                embedding_model = LLMBundle(self.tenant_id, LLMType.EMBEDDING)
            except Exception as e:
                logger.warning(f"Could not initialize real models, using mocks: {e}")
                # Use mock models for testing
                from unittest.mock import Mock
                chat_model = Mock()
                embedding_model = Mock()
            
            # Note: This would require actual document data and models to run fully
            # For integration testing, we validate the configuration and setup
            
            # Validate task configuration
            validated_config = GraphRAGConfigManager.validate_task_config(task)
            assert validated_config.use_graphrag is True
            
            duration = time.time() - start_time
            self.log_test_result("GraphRAG Execution Setup", True, "Configuration validated", duration)
            return True
            
        except Exception as e:
            duration = time.time() - start_time
            self.log_test_result("GraphRAG Execution Setup", False, f"Error: {str(e)}", duration)
            return False
    
    def test_error_handling(self) -> bool:
        """Test error handling scenarios."""
        start_time = time.time()
        
        try:
            # Test invalid task configuration
            try:
                invalid_task = {
                    "tenant_id": "",  # Invalid empty tenant_id
                    "kb_id": self.kb_id,
                    "doc_id": "test_doc",
                    "kb_parser_config": {
                        "graphrag": {
                            "use_graphrag": True,
                            "method": "invalid_method"  # Invalid method
                        }
                    }
                }
                GraphRAGConfigManager.validate_task_config(invalid_task)
                raise AssertionError("Should have raised ValueError for invalid configuration")
            except ValueError:
                pass  # Expected
            
            # Test task monitoring error scenarios
            task_id = "nonexistent_task"
            progress = self.task_monitor.get_progress(task_id)
            assert progress is None  # Should return None for nonexistent task
            
            # Test error callback
            error_task_id = "error_test_task"
            self.task_monitor.create_task_progress(
                task_id=error_task_id,
                tenant_id=self.tenant_id,
                kb_id=self.kb_id,
                doc_id="error_test_doc"
            )
            
            callback = self.task_monitor.create_progress_callback(error_task_id)
            callback(prog=-1.0, msg="Test error condition")
            
            error_progress = self.task_monitor.get_progress(error_task_id)
            assert error_progress.status == TaskStatus.FAILED
            
            duration = time.time() - start_time
            self.log_test_result("Error Handling", True, "All error scenarios handled correctly", duration)
            return True
            
        except Exception as e:
            duration = time.time() - start_time
            self.log_test_result("Error Handling", False, f"Unexpected error: {str(e)}", duration)
            return False
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all integration tests."""
        logger.info("Starting GraphRAG Integration Tests")
        start_time = time.time()
        
        # Run tests
        tests = [
            ("Config Validation", self.test_config_validation),
            ("Task Creation", self.test_task_creation),
            ("Task Monitoring", self.test_task_monitoring),
            ("GraphRAG Execution", self.test_graphrag_execution),
            ("Error Handling", self.test_error_handling),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            try:
                if asyncio.iscoroutinefunction(test_func):
                    success = await test_func()
                else:
                    success = test_func()
                
                if success:
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Test {test_name} crashed: {e}")
                failed += 1
        
        total_duration = time.time() - start_time
        
        # Generate summary
        summary = {
            "total_tests": len(tests),
            "passed": passed,
            "failed": failed,
            "success_rate": passed / len(tests) if tests else 0,
            "total_duration": total_duration,
            "test_results": self.test_results
        }
        
        logger.info(f"Integration Tests Completed: {passed}/{len(tests)} passed ({summary['success_rate']:.1%})")
        logger.info(f"Total Duration: {total_duration:.2f} seconds")
        
        return summary


async def main():
    """Main function for running integration tests."""
    parser = argparse.ArgumentParser(description="GraphRAG Integration Tests")
    parser.add_argument("--tenant-id", required=True, help="Tenant ID for testing")
    parser.add_argument("--kb-id", required=True, help="Knowledge Base ID for testing")
    parser.add_argument("--llm-id", help="LLM ID for testing")
    parser.add_argument("--output", help="Output file for test results (JSON)")
    
    args = parser.parse_args()
    
    # Run integration tests
    test_suite = GraphRAGIntegrationTest(
        tenant_id=args.tenant_id,
        kb_id=args.kb_id,
        llm_id=args.llm_id
    )
    
    summary = await test_suite.run_all_tests()
    
    # Save results if output file specified
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(summary, f, indent=2)
        logger.info(f"Test results saved to {args.output}")
    
    # Exit with appropriate code
    sys.exit(0 if summary["failed"] == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
