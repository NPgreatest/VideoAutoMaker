#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json

from wiki2video.methods.audio_engine import AudioEngineMethod


def try_audio_engine():
    """测试 AudioEngineMethod，输出到 _test_out/ 目录。"""
    workdir = Path("_test_out").resolve()
    project = "audio_demo"
    target_name = "sample1"

    # 随便写几句中文测试文本
    text = (
        "大家好，我是AI老高。今天我们来聊聊人工智能语音合成的未来。"
        "过去十年里，语音技术从简单的文本朗读，发展到了能模仿人类情感与语气的阶段。"
        "那么，未来AI的声音，会不会有一天与人类完全无异？"
    )

    print(f"🎧 生成音频测试输出目录: {workdir}")
    m = AudioEngineMethod()
    res = m.run(
        prompt="",
        project=project,
        target_name=target_name,
        text=text,
        workdir=workdir,
    )

    # 打印结果
    print("\n=== TTS 测试结果 ===")
    print(json.dumps(res, ensure_ascii=False, indent=2))

    if res["ok"]:
        print("\n✅ 音频生成成功！以下是主要文件：")
        for path in res["artifacts"]:
            print("  -", path)
    else:
        print("\n❌ 生成失败:", res["error"])


if __name__ == "__main__":
    try_audio_engine()
