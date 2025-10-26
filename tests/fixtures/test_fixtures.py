#!/usr/bin/env python3
"""
Test fixtures and utilities for the videogen pipeline tests.
This module provides reusable test components and setup utilities.
"""

import json
import tempfile
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class TestProject:
    """Test project configuration"""
    name: str
    workdir: Path
    project_dir: Path
    json_path: Path
    video_dir: Path
    audio_dir: Path
    subtitles_dir: Path


class TestDataFactory:
    """Factory for creating test data"""
    
    @staticmethod
    def create_test_project(name: str = "test_project") -> TestProject:
        """Create a test project structure"""
        temp_dir = tempfile.mkdtemp()
        workdir = Path(temp_dir)
        project_dir = workdir / "project" / name
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        video_dir = project_dir / "video"
        audio_dir = project_dir / "audio"
        subtitles_dir = project_dir / "subtitles"
        
        video_dir.mkdir(exist_ok=True)
        audio_dir.mkdir(exist_ok=True)
        subtitles_dir.mkdir(exist_ok=True)
        
        # Create JSON file
        json_path = project_dir / f"{name}.json"
        
        return TestProject(
            name=name,
            workdir=workdir,
            project_dir=project_dir,
            json_path=json_path,
            video_dir=video_dir,
            audio_dir=audio_dir,
            subtitles_dir=subtitles_dir
        )
    
    @staticmethod
    def create_openai_demo2_json(project_path: Path) -> None:
        """Create openai_demo2.json test data"""
        test_data = {
            "project": "openai_demo2",
            "script": [
                {
                    "id": "L1",
                    "text": "Back in 2015, OpenAI was born — a dream to make AI safe for everyone.",
                    "prompt": "A dimly lit office space filled with whiteboards covered in equations and diagrams.",
                    "context": "",
                    "voice": "Back in 2015, OpenAI was born — a dream to make AI safe for everyone.",
                    "character": "mark",
                    "decision": {
                        "method": "text_video",
                        "confidence": 1.0,
                        "decided_by": "llm"
                    },
                    "generation": {
                        "ok": True,
                        "artifacts": [],
                        "meta": {
                            "request_id": "mock_request_12345",
                            "project": "openai_demo2",
                            "target_name": "L1",
                            "status": "Submitted",
                            "output_path": "",
                            "source_url": "",
                            "submitted_at": "1761432124.847359"
                        },
                        "error": None,
                        "timestamp": "2025-10-25T22:42:04Z"
                    },
                    "audioGeneration": {
                        "ok": True,
                        "artifacts": [
                            "project/openai_demo2/audio/L1.wav"
                        ],
                        "meta": {
                            "project": "openai_demo2",
                            "target_name": "L1",
                            "character": "mark",
                            "voice_uri": "speech:mark:6ghs0srf2n:vcvzpeeoynxtwixefyyw",
                            "audio_path": "audio/L1.wav",
                            "total_duration": 6437.37
                        },
                        "error": None,
                        "timestamp": "2025-10-25T22:41:57Z"
                    },
                    "status": "done",
                    "retries": 0
                },
                {
                    "id": "L2",
                    "text": "Elon Musk and Sam Altman teamed up, promising to keep AI open and free.",
                    "prompt": "A sleek, futuristic conference hall bathed in cool blue light.",
                    "context": "",
                    "voice": "Elon Musk and Sam Altman teamed up, promising to keep AI open and free.",
                    "character": "mark",
                    "decision": {
                        "method": "text_video",
                        "confidence": 1.0,
                        "decided_by": "llm"
                    },
                    "generation": {
                        "ok": True,
                        "artifacts": [],
                        "meta": {
                            "request_id": "mock_request_67890",
                            "project": "openai_demo2",
                            "target_name": "L2",
                            "status": "Submitted",
                            "output_path": "",
                            "source_url": "",
                            "submitted_at": "1761432138.393995"
                        },
                        "error": None,
                        "timestamp": "2025-10-25T22:42:18Z"
                    },
                    "audioGeneration": {
                        "ok": True,
                        "artifacts": [
                            "project/openai_demo2/audio/L2.wav"
                        ],
                        "meta": {
                            "project": "openai_demo2",
                            "target_name": "L2",
                            "character": "mark",
                            "voice_uri": "speech:mark:6ghs0srf2n:vcvzpeeoynxtwixefyyw",
                            "audio_path": "audio/L2.wav",
                            "total_duration": 5717.37
                        },
                        "error": None,
                        "timestamp": "2025-10-25T22:42:10Z"
                    },
                    "status": "done",
                    "retries": 0
                }
            ],
            "updated_at": "2025-10-25T22:42:59+00:00"
        }
        
        with open(project_path, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, indent=2, ensure_ascii=False)
    
    @staticmethod
    def create_simple_project_json(project_path: Path) -> None:
        """Create a simple test project JSON"""
        test_data = {
            "project": "simple_test",
            "script": [
                {
                    "id": "S1",
                    "text": "This is a simple test script.",
                    "prompt": "A simple test scene.",
                    "context": "",
                    "voice": "This is a simple test script.",
                    "character": "mark",
                    "decision": {
                        "method": "text_video",
                        "confidence": 1.0,
                        "decided_by": "llm"
                    },
                    "status": "pending",
                    "retries": 0
                }
            ],
            "updated_at": "2025-10-25T22:42:59+00:00"
        }
        
        with open(project_path, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, indent=2, ensure_ascii=False)
    
    @staticmethod
    def create_csv_test_data(csv_path: Path) -> None:
        """Create test CSV data"""
        import csv
        
        test_data = [
            {
                "request_id": "test_123",
                "project": "test_project",
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
                "workdir": "/tmp/test",
                "duration": "5.0"
            }
        ]
        
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            if test_data:
                writer = csv.DictWriter(f, fieldnames=test_data[0].keys())
                writer.writeheader()
                writer.writerows(test_data)


class TestEnvironment:
    """Test environment manager"""
    
    def __init__(self):
        self.temp_dirs = []
        self.test_projects = []
    
    def create_test_project(self, name: str = None) -> TestProject:
        """Create a test project and track it for cleanup"""
        if name is None:
            name = f"test_project_{len(self.test_projects)}"
        
        project = TestDataFactory.create_test_project(name)
        self.test_projects.append(project)
        return project
    
    def cleanup(self):
        """Clean up all test resources"""
        import shutil
        
        for project in self.test_projects:
            if project.workdir.exists():
                shutil.rmtree(project.workdir, ignore_errors=True)
        
        self.test_projects.clear()
        self.temp_dirs.clear()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()


def create_test_video_file(video_path: Path, content: bytes = None) -> None:
    """Create a test video file"""
    if content is None:
        content = b"fake video content for testing"
    
    video_path.parent.mkdir(parents=True, exist_ok=True)
    video_path.write_bytes(content)


def create_test_audio_file(audio_path: Path, content: bytes = None) -> None:
    """Create a test audio file"""
    if content is None:
        # Minimal WAV file content
        content = b'RIFF\x24\x08\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x08\x00\x00' + b'\x00' * 1000
    
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    audio_path.write_bytes(content)
