#!/usr/bin/env python3
"""
Unit tests for the videogen methods.
This module tests individual method components.
"""

import unittest
from unittest.mock import Mock, patch
from pathlib import Path

# Import the modules we want to test
from videogen.methods.text_video_silicon.method import TextVideoSilicon
from videogen.methods.audio_silicon.method import SiliconAudioMethod, _tts_silicon_request
from videogen.methods.react_render.method import ReactRenderMethod

# Import test utilities
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from tests.fixtures.test_fixtures import TestEnvironment, TestDataFactory
from tests.mocks.api_mocks import MockAPIs, MockMethod


class TestTextVideoSilicon(unittest.TestCase):
    """Unit tests for TextVideoSilicon method"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_env = TestEnvironment()
        self.project = self.test_env.create_test_project("text_video_test")
    
    def tearDown(self):
        """Clean up test environment"""
        self.test_env.cleanup()
    
    def test_method_properties(self):
        """Test method properties"""
        method = TextVideoSilicon()
        self.assertEqual(method.NAME, "text_video")
        self.assertEqual(method.OUTPUT_KIND, "video")
    
    @patch('videogen.methods.text_video_silicon.method.submit_video')
    @patch('videogen.methods.text_video_silicon.method.TaskCSV')
    def test_text_video_method_run(self, mock_task_csv, mock_submit):
        """Test text video generation method"""
        # Setup mocks
        mock_submit.return_value = "mock_request_12345"
        mock_store = Mock()
        mock_task_csv.return_value = mock_store
        
        # Test video generation
        method = TextVideoSilicon()
        result = method.run(
            prompt="Test video prompt",
            project=self.project.name,
            target_name="test_video",
            text="Test video text",
            workdir=self.project.workdir,
            duration_ms=5000
        )
        
        # Verify result
        self.assertTrue(result["ok"])
        self.assertEqual(result["meta"]["request_id"], "mock_request_12345")
        self.assertEqual(result["meta"]["status"], "Submitted")
        
        # Verify submission was called
        mock_submit.assert_called_once_with("Test video prompt")
        mock_store.upsert.assert_called_once()
    
    def test_method_without_api_token(self):
        """Test method behavior without API token"""
        with patch('videogen.methods.text_video_silicon.method.SILICONFLOW_API_TOKEN', None):
            method = TextVideoSilicon()
            result = method.run(
                prompt="Test prompt",
                project=self.project.name,
                target_name="test_video",
                text="Test text",
                workdir=self.project.workdir
            )
            
            # Should return error without API token
            self.assertFalse(result["ok"])
            self.assertIn("Missing SILICONFLOW_API_TOKEN", result["error"])


class TestSiliconAudio(unittest.TestCase):
    """Unit tests for SiliconAudio method"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_env = TestEnvironment()
        self.project = self.test_env.create_test_project("audio_test")
    
    def tearDown(self):
        """Clean up test environment"""
        self.test_env.cleanup()
    
    def test_method_properties(self):
        """Test method properties"""
        method = SiliconAudioMethod()
        self.assertEqual(method.NAME, "silicon_audio")
        self.assertEqual(method.OUTPUT_KIND, "audio")
    
    @patch('videogen.methods.audio_silicon.method.requests.post')
    @patch('videogen.methods.audio_silicon.method.ensure_voice_uri')
    @patch('videogen.methods.audio_silicon.method.list_cached_voices')
    @patch('videogen.methods.audio_silicon.method.get_default_character')
    def test_audio_generation(self, mock_get_default_char, mock_list_cached, mock_ensure_voice, mock_post):
        """Test audio generation with mocked TTS API"""
        # Setup mocks
        mock_get_default_char.return_value = "mark"
        mock_list_cached.return_value = ["mark", "laogao"]
        mock_ensure_voice.return_value = "speech:mark:6ghs0srf2n:vcvzpeeoynxtwixefyyw"
        
        # Mock successful TTS response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = MockAPIs.get_tts_response()
        mock_post.return_value = mock_response
        
        # Test audio generation
        method = SiliconAudioMethod()
        result = method.run(
            prompt="Test prompt",
            project=self.project.name,
            target_name="test_audio",
            text="Test audio text",
            workdir=self.project.workdir,
            block=None
        )
        
        # Verify result
        self.assertTrue(result["ok"])
        self.assertIn("artifacts", result)
        self.assertIn("meta", result)
        self.assertIsNone(result["error"])
        
        # Verify API was called
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[1]['json']['input'], "Test audio text")
    
    def test_tts_request_function(self):
        """Test TTS request function directly"""
        with patch('videogen.methods.audio_silicon.method.requests.post') as mock_post:
            # Mock successful response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = MockAPIs.get_tts_response()
            mock_post.return_value = mock_response
            
            # Test TTS request
            test_path = self.project.audio_dir / "test.wav"
            result = _tts_silicon_request("Test text", test_path, {"input": "Test text"})
            
            # Verify result
            self.assertTrue(result)
            self.assertTrue(test_path.exists())
            mock_post.assert_called_once()
    
    def test_audio_generation_no_text(self):
        """Test audio generation with no input text"""
        method = SiliconAudioMethod()
        result = method.run(
            prompt="",
            project=self.project.name,
            target_name="test_audio",
            text="",
            workdir=self.project.workdir,
            block=None
        )
        
        # Should return error for no input
        self.assertFalse(result["ok"])
        self.assertIn("No input text provided", result["error"])


class TestReactRender(unittest.TestCase):
    """Unit tests for ReactRender method"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_env = TestEnvironment()
        self.project = self.test_env.create_test_project("react_test")
    
    def tearDown(self):
        """Clean up test environment"""
        self.test_env.cleanup()
    
    def test_method_properties(self):
        """Test method properties"""
        method = ReactRenderMethod()
        self.assertEqual(method.NAME, "react_animation")
        self.assertEqual(method.OUTPUT_KIND, "video")
        self.assertEqual(method.DEFAULT_W, 1920)
        self.assertEqual(method.DEFAULT_H, 1080)
        self.assertEqual(method.DEFAULT_SEC, 10.0)
    
    def test_prompt_generation(self):
        """Test prompt generation method"""
        method = ReactRenderMethod()
        
        # Test that generate_prompt method exists and is callable
        self.assertTrue(hasattr(method, 'generate_prompt'))
        self.assertTrue(callable(method.generate_prompt))
        
        # Test with mock LLM engine
        with patch('videogen.methods.react_render.method.get_engine') as mock_get_engine:
            mock_engine = Mock()
            mock_engine.chat.return_value = {"content": "Generated prompt"}
            mock_get_engine.return_value = mock_engine
            
            result = method.generate_prompt("Test animation text")
            
            # Verify LLM was called
            mock_engine.chat.assert_called_once()
            self.assertIsInstance(result, str)
    
    def test_method_run_validation(self):
        """Test method run with validation"""
        method = ReactRenderMethod()
        
        # Test with empty text
        result = method.run(
            prompt="Test prompt",
            project=self.project.name,
            target_name="test_react",
            text="",
            workdir=self.project.workdir
        )
        
        # Should return error for empty text
        self.assertFalse(result["ok"])
        self.assertIn("text 不能为空", result["error"])


class TestMethodIntegration(unittest.TestCase):
    """Integration tests for method functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_env = TestEnvironment()
        self.project = self.test_env.create_test_project("method_integration_test")
    
    def tearDown(self):
        """Clean up test environment"""
        self.test_env.cleanup()
    
    def test_method_registration(self):
        """Test that methods are properly registered"""
        from videogen.methods.registry import create_method
        
        # Test creating different methods
        text_video_method = create_method("text_video")
        self.assertIsInstance(text_video_method, TextVideoSilicon)
        
        audio_method = create_method("silicon_audio")
        self.assertIsInstance(audio_method, SiliconAudioMethod)
        
        react_method = create_method("react_animation")
        self.assertIsInstance(react_method, ReactRenderMethod)
    
    def test_method_workflow_integration(self):
        """Test method workflow integration"""
        # Test that methods can be created and have required methods
        methods = [
            TextVideoSilicon(),
            SiliconAudioMethod(),
            ReactRenderMethod()
        ]
        
        for method in methods:
            # All methods should have these properties
            self.assertTrue(hasattr(method, 'NAME'))
            self.assertTrue(hasattr(method, 'OUTPUT_KIND'))
            self.assertTrue(hasattr(method, 'run'))
            self.assertTrue(callable(method.run))
            
            # All methods should have generate_prompt method
            self.assertTrue(hasattr(method, 'generate_prompt'))
            self.assertTrue(callable(method.generate_prompt))


if __name__ == "__main__":
    unittest.main()
