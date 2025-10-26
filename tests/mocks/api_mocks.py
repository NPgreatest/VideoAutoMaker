#!/usr/bin/env python3
"""
Mock API responses for testing the videogen pipeline.
This module provides centralized mock responses for all external APIs.
"""

from typing import Dict, Any, List
from unittest.mock import Mock


class MockAPIs:
    """Centralized mock responses for all external APIs"""
    
    @staticmethod
    def get_llm_response(method: str) -> str:
        """Mock LLM responses for different methods"""
        responses = {
            "decider": "text_video",
            "prompt_generator": "A cinematic scene showing the described content with dramatic lighting and composition.",
            "react_prompt": "Create an animated visualization with charts and data visualization elements.",
            "validation": "True"
        }
        return responses.get(method, "Mocked response")
    
    @staticmethod
    def get_siliconflow_submit_response() -> Dict[str, Any]:
        """Mock SiliconFlow video submission response"""
        return {
            "requestId": "mock_request_12345",
            "status": "Submitted",
            "message": "Task submitted successfully"
        }
    
    @staticmethod
    def get_siliconflow_status_response() -> Dict[str, Any]:
        """Mock SiliconFlow status check response"""
        return {
            "status": "Succeed",
            "results": {
                "videos": [{
                    "url": "https://file-examples.com/wp-content/storage/2017/04/file_example_MP4_480_1_5MG.mp4",
                    "duration": 5.0
                }]
            }
        }
    
    @staticmethod
    def get_tts_response() -> bytes:
        """Mock TTS audio response (fake WAV file)"""
        # This is a minimal WAV file header for testing
        return b'RIFF\x24\x08\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x08\x00\x00' + b'\x00' * 1000
    
    @staticmethod
    def get_playwright_mock():
        """Mock Playwright browser automation"""
        mock_browser = Mock()
        mock_context = Mock()
        mock_page = Mock()
        mock_page.video.return_value.path.return_value = "/tmp/test.webm"
        mock_context.new_page.return_value = mock_page
        mock_browser.new_context.return_value = mock_context
        
        mock_playwright = Mock()
        # Create a proper context manager mock
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_playwright)
        mock_context_manager.__exit__ = Mock(return_value=None)
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_playwright.return_value = mock_context_manager
        return mock_playwright
    
    @staticmethod
    def get_requests_mock_response(status_code: int = 200, content: bytes = None, json_data: Dict = None):
        """Create a mock requests response"""
        mock_response = Mock()
        mock_response.status_code = status_code
        
        if content is not None:
            mock_response.content = content
            mock_response.iter_content.return_value = [content]
            # Add context manager support
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=None)
        
        if json_data is not None:
            mock_response.json.return_value = json_data
        
        return mock_response
    
    @staticmethod
    def get_ffmpeg_mock():
        """Mock FFmpeg subprocess calls"""
        mock_result = Mock()
        mock_result.returncode = 0
        return mock_result


class MockEngine:
    """Mock LLM engine for testing"""
    
    def __init__(self):
        self.chat_calls = []
        self.ask_text_calls = []
    
    def chat(self, messages: List[Dict], temperature: float = 0.7, max_tokens: int = 100):
        """Mock chat method"""
        self.chat_calls.append({
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        })
        
        # Return appropriate response based on the system prompt
        system_content = messages[0]["content"] if messages else ""
        if "decider" in system_content.lower() or "director" in system_content.lower():
            return {"content": "text_video"}
        elif "validator" in system_content.lower():
            return {"content": "True"}
        else:
            return {"content": "Mocked response"}
    
    def ask_text(self, prompt: str) -> str:
        """Mock ask_text method"""
        self.ask_text_calls.append(prompt)
        
        if "React" in prompt or "animation" in prompt:
            return """
            <script type="text/babel">
            const { useState, useEffect } = React;
            function App() {
                const [count, setCount] = useState(0);
                useEffect(() => {
                    const timer = setInterval(() => setCount(c => c + 1), 100);
                    setTimeout(() => window.__PLAY_DONE = true, 2000);
                    return () => clearInterval(timer);
                }, []);
                return <div style={{textAlign: 'center', fontSize: '48px'}}>{count}</div>;
            }
            ReactDOM.render(<App />, document.getElementById('root'));
            </script>
            """
        else:
            return "A cinematic scene showing the described content with dramatic lighting and composition."


class MockTaskCSV:
    """Mock TaskCSV for testing"""
    
    def __init__(self, db_path):
        self.db_path = db_path
        self.data = []
        self.upsert_calls = []
    
    def upsert(self, row: Dict[str, Any]):
        """Mock upsert method"""
        self.upsert_calls.append(row)
        # Update existing or add new
        for i, existing in enumerate(self.data):
            if existing.get("request_id") == row.get("request_id"):
                self.data[i] = row
                return
        self.data.append(row)
    
    def get_all(self) -> List[Dict[str, Any]]:
        """Mock get_all method"""
        return self.data.copy()


class MockMethod:
    """Mock method for testing"""
    
    def __init__(self, name: str = "test_method"):
        self.name = name
        self.run_calls = []
        self.generate_prompt_calls = []
    
    def run(self, **kwargs):
        """Mock run method"""
        self.run_calls.append(kwargs)
        return {
            "ok": True,
            "artifacts": [f"test_{kwargs.get('target_name', 'output')}.mp4"],
            "meta": {
                "request_id": "mock_request_12345",
                "status": "Submitted",
                "project": kwargs.get("project", "test_project"),
                "target_name": kwargs.get("target_name", "test_output")
            },
            "error": None
        }
    
    def generate_prompt(self, text: str) -> str:
        """Mock generate_prompt method"""
        self.generate_prompt_calls.append(text)
        return f"Generated prompt for: {text}"


def create_mock_environment():
    """Create a complete mock environment for testing"""
    return {
        "llm_engine": MockEngine(),
        "task_csv": MockTaskCSV("/tmp/test.csv"),
        "text_video_method": MockMethod("text_video"),
        "audio_method": MockMethod("silicon_audio"),
        "react_method": MockMethod("react_animation"),
        "requests_mock": Mock(),
        "playwright_mock": MockAPIs.get_playwright_mock(),
        "ffmpeg_mock": MockAPIs.get_ffmpeg_mock()
    }
