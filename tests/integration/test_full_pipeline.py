#!/usr/bin/env python3
"""
Integration tests for the full videogen pipeline.
This module tests the complete pipeline flow with mocked APIs.
"""

import unittest
from unittest.mock import Mock, patch
from pathlib import Path

# Import the modules we want to test
from videogen.pipeline.pipeline import run_pipeline
from videogen.methods.text_video_silicon.worker import start_worker_loop
from videogen.methods.text_video_silicon.store import TaskCSV

# Import test utilities
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from tests.fixtures.test_fixtures import TestEnvironment, TestDataFactory
from tests.mocks.api_mocks import MockAPIs, create_mock_environment


class TestFullPipelineIntegration(unittest.TestCase):
    """Integration tests for the full pipeline"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_env = TestEnvironment()
        self.project = self.test_env.create_test_project("full_pipeline_test")
        TestDataFactory.create_openai_demo2_json(self.project.json_path)
    
    def tearDown(self):
        """Clean up test environment"""
        self.test_env.cleanup()
    
    @patch('videogen.pipeline.pipeline.decide_generation_method')
    @patch('videogen.pipeline.pipeline.create_method')
    @patch('videogen.pipeline.pipeline._wait_for_video_completion')
    def test_full_pipeline_with_decision_generation(self, mock_wait_completion, mock_create_method, mock_decide):
        """Test full pipeline with decision generation"""
        # Setup mocks
        mock_decide.return_value = "text_video"
        
        mock_method = Mock()
        mock_method.generate_prompt.return_value = "Generated prompt"
        mock_method.run.return_value = {
            "ok": True,
            "artifacts": [str(self.project.video_dir / "test.mp4")],
            "meta": {"request_id": "test_123", "status": "Submitted"},
            "error": None
        }
        mock_create_method.return_value = mock_method
        
        # Test full pipeline run
        run_pipeline(
            input_path=self.project.json_path,
            workdir=self.project.workdir,
            genDecision=True,
            genAudio=False,
            genPrompt=True,
            genMedia=True
        )
        
        # Verify mocks were called
        mock_create_method.assert_called()
        mock_method.run.assert_called()
        mock_wait_completion.assert_called()
    
    @patch('videogen.pipeline.pipeline.create_method')
    @patch('videogen.pipeline.pipeline._wait_for_video_completion')
    def test_full_pipeline_audio_generation(self, mock_wait_completion, mock_create_method):
        """Test full pipeline with audio generation"""
        # Setup mocks
        mock_audio_method = Mock()
        mock_audio_method.run.return_value = {
            "ok": True,
            "artifacts": [str(self.project.audio_dir / "test.wav")],
            "meta": {"total_duration": 5000},
            "error": None
        }
        
        mock_video_method = Mock()
        mock_video_method.run.return_value = {
            "ok": True,
            "artifacts": [str(self.project.video_dir / "test.mp4")],
            "meta": {"request_id": "test_123", "status": "Submitted"},
            "error": None
        }
        
        # Mock create_method to return different methods based on call
        def mock_create_side_effect(method_name):
            if method_name == 'silicon_audio':
                return mock_audio_method
            else:
                return mock_video_method
        
        mock_create_method.side_effect = mock_create_side_effect
        
        # Test pipeline with audio generation
        run_pipeline(
            input_path=self.project.json_path,
            workdir=self.project.workdir,
            genDecision=False,
            genAudio=True,
            genPrompt=False,
            genMedia=True
        )
        
        # Verify audio method was called
        mock_audio_method.run.assert_called()
        mock_video_method.run.assert_called()
        mock_wait_completion.assert_called()
    
    def test_pipeline_with_existing_completed_tasks(self):
        """Test pipeline behavior with already completed tasks"""
        # The test JSON already has completed tasks
        # Pipeline should skip them
        run_pipeline(
            input_path=self.project.json_path,
            workdir=self.project.workdir,
            genDecision=False,
            genAudio=False,
            genPrompt=False,
            genMedia=False
        )
        
        # Should complete without errors
        self.assertTrue(True)  # If we get here, no exceptions were raised
    
    @patch('videogen.methods.text_video_silicon.worker.check_status')
    @patch('videogen.methods.text_video_silicon.worker.download_to')
    @patch('videogen.methods.text_video_silicon.worker.resize_video_duration')
    def test_worker_integration_with_pipeline(self, mock_resize, mock_download, mock_check_status):
        """Test worker integration with pipeline"""
        # Setup mocks
        mock_resize.return_value = 5.0
        mock_check_status.return_value = {
            "status": "Succeed",
            "results": {
                "videos": [{"url": "https://mock-cdn.example.com/video123.mp4"}]
            }
        }
        
        # Create test CSV data
        import csv
        db_path = self.project.workdir / "db" / "video_download.csv"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        test_csv_data = [
            {
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
        ]
        
        with open(db_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=test_csv_data[0].keys())
            writer.writeheader()
            writer.writerows(test_csv_data)
        
        # Test worker loop
        import threading
        import time
        
        def run_worker_with_timeout():
            try:
                store = TaskCSV(db_path)
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
    
    def test_video_folder_structure_integration(self):
        """Test video folder structure in integration"""
        # Create test videos in the new structure
        test_video = self.project.video_dir / "integration_test.mp4"
        test_raw_video = self.project.video_dir / "integration_test_raw.mp4"
        
        test_video.write_bytes(b"fake processed video content")
        test_raw_video.write_bytes(b"fake raw video content")
        
        # Verify structure
        self.assertTrue(self.project.video_dir.exists())
        self.assertTrue(test_video.exists())
        self.assertTrue(test_raw_video.exists())
        
        # Verify paths are correct
        expected_video_path = self.project.project_dir / "video" / "integration_test.mp4"
        expected_raw_path = self.project.project_dir / "video" / "integration_test_raw.mp4"
        
        self.assertEqual(str(test_video), str(expected_video_path))
        self.assertEqual(str(test_raw_video), str(expected_raw_path))
    
    def test_project_json_structure_integration(self):
        """Test project JSON structure integration"""
        # Verify JSON file is valid and has expected structure
        import json
        
        with open(self.project.json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            # Check top-level structure
            self.assertIn("project", data)
            self.assertIn("script", data)
            self.assertIn("updated_at", data)
            
            # Check script structure
            self.assertIsInstance(data["script"], list)
            self.assertGreater(len(data["script"]), 0)
            
            # Check script item structure
            script_item = data["script"][0]
            self.assertIn("id", script_item)
            self.assertIn("text", script_item)
            self.assertIn("prompt", script_item)
            self.assertIn("decision", script_item)
            self.assertIn("generation", script_item)
            self.assertIn("audioGeneration", script_item)
            self.assertIn("status", script_item)
    
    def test_error_handling_integration(self):
        """Test error handling in integration"""
        # Test with non-existent JSON file
        non_existent_path = self.project.workdir / "non_existent.json"
        
        with self.assertRaises(FileNotFoundError):
            run_pipeline(
                input_path=non_existent_path,
                workdir=self.project.workdir,
                genDecision=True,
                genAudio=False,
                genPrompt=False,
                genMedia=False
            )
    
    def test_mock_environment_integration(self):
        """Test mock environment integration"""
        # Test that mock environment works correctly
        mock_env = create_mock_environment()
        
        # Verify all mock components exist
        self.assertIn("llm_engine", mock_env)
        self.assertIn("task_csv", mock_env)
        self.assertIn("text_video_method", mock_env)
        self.assertIn("audio_method", mock_env)
        self.assertIn("react_method", mock_env)
        
        # Test mock LLM engine
        llm_engine = mock_env["llm_engine"]
        response = llm_engine.chat([{"role": "system", "content": "Test"}, {"role": "user", "content": "Test"}])
        self.assertIn("content", response)
        
        # Test mock methods
        text_video_method = mock_env["text_video_method"]
        result = text_video_method.run(
            prompt="Test prompt",
            project="test_project",
            target_name="test_video",
            text="Test text",
            workdir=self.project.workdir
        )
        self.assertTrue(result["ok"])


if __name__ == "__main__":
    unittest.main()
