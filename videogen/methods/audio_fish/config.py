#!/usr/bin/env python3
from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Dict, Any
import requests
from dotenv import load_dotenv



# ========== 环境加载 ==========
load_dotenv()
AUDIO_FISH_API_KEY = os.getenv("AUDIO_FISH_API_KEY")
from fish_audio_sdk import Session, TTSRequest

session = Session(AUDIO_FISH_API_KEY)

# ========== 路径定义 ==========
# 从当前文件位置向上找到项目根目录，然后定位到 config 目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

