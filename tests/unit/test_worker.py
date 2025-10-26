#!/usr/bin/env python3
"""
Unit tests for the worker functionality.
This module tests the worker loop and video processing.
"""

import unittest
from unittest.mock import Mock, patch
from pathlib import Path
import tempfile
import csv

# Import the modules we want to test
from videogen.methods.text_video_silicon.worker import start_worker_loop, check_and_resize_missing_final_videos
from videogen.methods.text_video_silicon.store import TaskCSV
from videogen.methods.text_video_silicon.sf_api import submit_video, check_status, download_to

# Import test utilities
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from tests.fixtures.test_fixtures import TestEnvironment, TestDataFactory
from tests.mocks.api_mocks import MockAPIs, MockTaskCSV


class TestWorkerUnit(unittest.TestCase):
    """Unit tests for worker components"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_env = TestEnvironment()
        self.project = self.test_env.create_test_project("worker_test")
        self.db_path = self.project.workdir / "db" / "video_download.csv"
        TestDataFactory.create_csv_test_data(self.db_path)
    
    def tearDown(self):
        """Clean up test environment"""
        self.test_env.cleanup()
    
    @patch('videogen.methods.text_video_silicon.sf_api.requests.post')
    def test_video_submission(self, mock_post):
        """Test video submission with mocked SiliconFlow API"""
        # Mock successful submission response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = MockAPIs.get_siliconflow_submit_response()
        mock_post.return_value = mock_response
        
        # Test video submission
        request_id = submit_video("Test video prompt")
        
        # Verify result
        self.assertEqual(request_id, "mock_request_12345")
        mock_post.assert_called_once()
    
    @patch('videogen.methods.text_video_silicon.sf_api.requests.post')
    def test_video_status_check(self, mock_post):
        """Test video status checking with mocked API"""
        # Mock successful status response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = MockAPIs.get_siliconflow_status_response()
        mock_post.return_value = mock_response
        
        # Test status check
        result = check_status("mock_request_12345")
        
        # Verify result
        self.assertIn("status", result)
        if result["status"] == "Succeed":
            self.assertIn("results", result)
        mock_post.assert_called_once()
    
    @patch('videogen.methods.text_video_silicon.sf_api.requests.get')
    def test_video_download(self, mock_get):
        """Test video download with mocked API"""
        # Mock successful download response with context manager support
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [b"fake video content"]
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=None)
        mock_get.return_value = mock_response
        
        # Test video download
        test_video_path = self.project.video_dir / "test_video.mp4"
        download_to("https://mock-cdn.example.com/video123.mp4", test_video_path)
        
        # Verify file was created
        self.assertTrue(test_video_path.exists())
        self.assertEqual(test_video_path.read_bytes(), b"fake video content")
        mock_get.assert_called_once()
    
    def test_csv_database_operations(self):
        """Test CSV database operations"""
        # Create test data
        test_data = {
            "request_id": "test_123",
            "project": self.project.name,
            "target_name": "test_video",
            "prompt": "Test prompt",
            "model": "test_model",
            "status": "Submitted",
            "output_path": "",
            "source_url": "",
            "created_ts": "1234567890",
            "updated_ts": "1234567890",
            "error": "",
            "poll_count": "0",
            "workdir": str(self.project.workdir),
            "duration": "5.0"
        }
        
        # Test CSV operations
        store = TaskCSV(self.db_path)
        store.upsert(test_data)
        
        # Verify data was stored
        all_data = store.get_all()
        self.assertEqual(len(all_data), 1)
        self.assertEqual(all_data[0]["request_id"], "test_123")
        self.assertEqual(all_data[0]["project"], self.project.name)
    
    @patch('videogen.methods.text_video_silicon.worker.check_status')
    @patch('videogen.methods.text_video_silicon.worker.download_to')
    @patch('videogen.methods.text_video_silicon.worker.resize_video_duration')
    def test_worker_loop_processing(self, mock_resize, mock_download, mock_check_status):
        """Test worker loop processing with mocked APIs"""
        # Setup mocks
        mock_resize.return_value = 5.0
        mock_check_status.return_value = {
            "status": "Succeed",
            "results": {
                "videos": [{"url": "https://mock-cdn.example.com/video123.mp4"}]
            }
        }
        
        # Create test CSV data
        test_csv_data = [
            {
                "request_id": "test_123",
                "project": self.project.name,
                "target_name": "test_video",
                "prompt": "Test prompt",
                "model": "test_model",
                "status": "Submitted",
                "output_path": "",
                "source_url": "",
                "created_ts": "1234567890",
                "updated_ts": "1234567890",
                "error": "",
                "poll_count": "0",
                "workdir": str(self.project.workdir),
                "duration": "5.0"
            }
        ]
        
        # Create mock CSV file
        with open(self.db_path, 'w', newline='', encoding='utf-8') as f:
            if test_csv_data:
                writer = csv.DictWriter(f, fieldnames=test_csv_data[0].keys())
                writer.writeheader()
                writer.writerows(test_csv_data)
        
        # Test worker loop (with timeout to prevent infinite loop)
        import threading
        import time
        
        def run_worker_with_timeout():
            try:
                store = TaskCSV(self.db_path)
                start_worker_loop(store)
            except Exception as e:
                print(f"Worker loop error: {e}")
        
        # Run worker in separate thread with timeout
        worker_thread = threading.Thread(target=run_worker_with_timeout)
        worker_thread.daemon = True
        worker_thread.start()
        
        # Wait a bit for processing
        time.sleep(1)
        
        # Verify mocks were called
        mock_check_status.assert_called()
    
    def test_repair_missing_videos(self):
        """Test repair functionality for missing final videos"""
        # Create a raw video file but no final video
        raw_video = self.project.video_dir / "test_video_raw.mp4"
        raw_video.write_bytes(b"fake raw video content")
        
        # Create test CSV data with raw-only video
        test_data = {
            "request_id": "test_123",
            "project": self.project.name,
            "target_name": "test_video",
            "prompt": "Test prompt",
            "model": "test_model",
            "status": "Submitted",
            "output_path": "",
            "source_url": "",
            "created_ts": "1234567890",
            "updated_ts": "1234567890",
            "error": "",
            "poll_count": "0",
            "workdir": str(self.project.workdir),
            "duration": "5.0"
        }
        
        store = TaskCSV(self.db_path)
        store.upsert(test_data)
        
        # Test repair functionality
        with patch('videogen.methods.text_video_silicon.worker.resize_video_duration') as mock_resize:
            mock_resize.return_value = 5.0
            check_and_resize_missing_final_videos(store)
        
        # Verify repair was attempted
        mock_resize.assert_called()


class TestWorkerIntegration(unittest.TestCase):
    """Integration tests for worker functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_env = TestEnvironment()
        self.project = self.test_env.create_test_project("worker_integration_test")
        self.db_path = self.project.workdir / "db" / "video_download.csv"
    
    def tearDown(self):
        """Clean up test environment"""
        self.test_env.cleanup()
    
    def test_worker_database_integration(self):
        """Test worker database integration"""
        # Create test data
        test_data = {
            "request_id": "integration_test_123",
            "project": self.project.name,
            "target_name": "integration_video",
            "prompt": "Integration test prompt",
            "model": "test_model",
            "status": "Submitted",
            "output_path": "",
            "source_url": "",
            "created_ts": "1234567890",
            "updated_ts": "1234567890",
            "error": "",
            "poll_count": "0",
            "workdir": str(self.project.workdir),
            "duration": "5.0"
        }
        
        # Test database operations
        store = TaskCSV(self.db_path)
        store.upsert(test_data)
        
        # Verify data persistence
        all_data = store.get_all()
        self.assertEqual(len(all_data), 1)
        self.assertEqual(all_data[0]["request_id"], "integration_test_123")
        
        # Test update
        test_data["status"] = "Succeed"
        test_data["output_path"] = str(self.project.video_dir / "integration_video.mp4")
        store.upsert(test_data)
        
        # Verify update
        updated_data = store.get_all()
        self.assertEqual(updated_data[0]["status"], "Succeed")
        self.assertIn("integration_video.mp4", updated_data[0]["output_path"])


if __name__ == "__main__":
    unittest.main()
