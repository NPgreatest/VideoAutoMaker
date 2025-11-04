#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json

from videogen.methods.audio_silicon import SiliconAudioMethod
from videogen.methods.audio_silicon.config import ensure_voice_uri, list_cached_voices, get_default_character


def try_audio_engine():
    """测试 SiliconAudioMethod，生成默认角色和 Mark 角色的两段音频。"""
    workdir = Path("_test_out").resolve()
    project = "audio_demo_silicon"

    # ===================== 测试文本 =====================
    text_default = (
        "大家好，我是AI老高。今天我们来聊聊人工智能语音合成的未来。"
        "过去十年里，语音技术从简单的文本朗读，发展到了能模仿人类情感与语气的阶段。"
        "那么，未来AI的声音，会不会有一天与人类完全无异？"
    )

    text_mark = (
        "Hello everyone, I'm Mark. Today, let's talk about how AI voices "
        "are transforming the way we communicate with machines. "
        "Maybe one day, AI will sound more human than humans themselves."
    )

    # ===================== 检查缓存的角色 =====================
    cached = list_cached_voices()
    print(f"🎭 当前已缓存角色: {list(cached.keys()) or '无缓存'}")

    default_character = get_default_character()
    print(f"🟢 默认角色: {default_character}")

    # ===================== 测试 1: 默认角色 =====================
    print("\n🎧 生成默认角色音频...")
    m = SiliconAudioMethod()
    res_default = m.run(
        prompt="",
        project=project,
        target_name="sample_default",
        text=text_default,
        workdir=workdir,
        # 没有传 character，内部会自动选择默认角色
    )

    print("\n=== 默认角色音频结果 ===")
    print(json.dumps(res_default, ensure_ascii=False, indent=2))

    # ===================== 测试 2: 新角色 Mark =====================
    print("\n🎤 检查或上传角色 'Mark' 的参考音频...")
    ensure_voice_uri("mark")  # 自动上传/缓存

    print("\n🎧 生成 Mark 角色音频...")
    block = type("DummyBlock", (), {"text": text_mark, "character": "mark"})()
    res_mark = m.run(
        prompt="",
        project=project,
        target_name="sample_mark",
        text=text_mark,
        workdir=workdir,
        block=block,
    )

    print("\n=== Mark 角色音频结果 ===")
    print(json.dumps(res_mark, ensure_ascii=False, indent=2))

    # ===================== 输出结果 =====================
    print("\n📦 生成文件汇总：")
    for res in [res_default, res_mark]:
        if res.get("ok"):
            for path in res["artifacts"]:
                print("  -", path)
        else:
            print(f"  ❌ {res.get('error')}")

    print("\n✅ 测试完成！音频已输出到：", workdir / "project" / project / "audio")


if __name__ == "__main__":
    try_audio_engine()
