#!/usr/bin/env python3
"""
Unit tests for the videogen pipeline.
This module tests individual pipeline components in isolation.
"""

import unittest
from unittest.mock import Mock, patch
from pathlib import Path

# Import the modules we want to test
from videogen.pipeline.pipeline import run_pipeline, _wait_for_video_completion
from videogen.router.decider import decide_generation_method

# Import test utilities
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from tests.fixtures.test_fixtures import TestEnvironment, TestDataFactory
from tests.mocks.api_mocks import MockAPIs, MockEngine


class TestPipelineUnit(unittest.TestCase):
    """Unit tests for pipeline components"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_env = TestEnvironment()
        self.project = self.test_env.create_test_project("unit_test")
        TestDataFactory.create_openai_demo2_json(self.project.json_path)
    
    def tearDown(self):
        """Clean up test environment"""
        self.test_env.cleanup()
    
    @patch('videogen.router.decider.get_engine')
    def test_decide_generation_method(self, mock_get_engine):
        """Test the decision making process"""
        # Mock LLM engine
        mock_engine = MockEngine()
        mock_get_engine.return_value = mock_engine
        
        # Test decision making
        method = decide_generation_method("Test text", "test_topic")
        self.assertEqual(method, "text_video")
        
        # Verify LLM was called
        self.assertEqual(len(mock_engine.chat_calls), 1)
        call_args = mock_engine.chat_calls[0]
        self.assertEqual(len(call_args["messages"]), 2)  # system + user message
    
    @patch('videogen.pipeline.pipeline.decide_generation_method')
    @patch('videogen.pipeline.pipeline.create_method')
    @patch('videogen.pipeline.pipeline._wait_for_video_completion')
    def test_pipeline_run_decision_generation(self, mock_wait_completion, mock_create_method, mock_decide):
        """Test pipeline run with decision generation"""
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
        
        # Test pipeline run (automatically generates audio and video if missing)
        run_pipeline(
            input_path=self.project.json_path,
            workdir=self.project.workdir
        )
        
        # Verify mocks were called
        mock_create_method.assert_called()
        mock_method.run.assert_called()
        mock_wait_completion.assert_called()
    
    @patch('videogen.pipeline.pipeline.create_method')
    @patch('videogen.pipeline.pipeline._wait_for_video_completion')
    def test_pipeline_run_skip_completed(self, mock_wait_completion, mock_create_method):
        """Test pipeline run skips already completed tasks"""
        # Setup mocks
        mock_method = Mock()
        mock_create_method.return_value = mock_method
        
        # Test pipeline run (should skip completed tasks if they exist)
        run_pipeline(
            input_path=self.project.json_path,
            workdir=self.project.workdir
        )
        
        # Verify no method calls were made for completed tasks
        mock_method.run.assert_not_called()
        mock_wait_completion.assert_not_called()
    
    def test_pipeline_error_handling(self):
        """Test pipeline error handling"""
        # Test with non-existent file
        non_existent_path = self.project.workdir / "non_existent.json"
        
        with self.assertRaises(FileNotFoundError):
            run_pipeline(
                input_path=non_existent_path,
                workdir=self.project.workdir
            )


class TestPipelineIntegration(unittest.TestCase):
    """Integration tests for pipeline components"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_env = TestEnvironment()
        self.project = self.test_env.create_test_project("integration_test")
        TestDataFactory.create_simple_project_json(self.project.json_path)
    
    def tearDown(self):
        """Clean up test environment"""
        self.test_env.cleanup()
    
    def test_video_folder_structure(self):
        """Test that the new video folder structure is used"""
        # Create a test video file in the video folder
        test_video = self.project.video_dir / "test_video.mp4"
        test_video.write_bytes(b"fake video content")
        
        # Verify the structure
        self.assertTrue(self.project.video_dir.exists())
        self.assertTrue(test_video.exists())
        
        # Verify the path structure
        expected_path = self.project.project_dir / "video" / "test_video.mp4"
        self.assertEqual(str(test_video), str(expected_path))
    
    def test_project_structure_creation(self):
        """Test that project structure is created correctly"""
        # Verify all directories exist
        self.assertTrue(self.project.project_dir.exists())
        self.assertTrue(self.project.video_dir.exists())
        self.assertTrue(self.project.audio_dir.exists())
        self.assertTrue(self.project.subtitles_dir.exists())
        self.assertTrue(self.project.json_path.exists())
        
        # Verify JSON file is valid
        import json
        with open(self.project.json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.assertIn("project", data)
            self.assertIn("script", data)


if __name__ == "__main__":
    unittest.main()
