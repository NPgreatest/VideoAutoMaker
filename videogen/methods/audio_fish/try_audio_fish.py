#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from videogen.methods.audio_fish.method import FishAudioMethod


def try_audio_engine():
    """测试 SiliconAudioMethod，生成默认角色和 Mark 角色的两段音频。"""
    workdir = Path("_test_out").resolve()
    project = "audio_demo_fish"

    # ===================== 测试文本 =====================
    text_huzi = (
        "一个城市只要没有山姆超市，就完全不值得去。"
    )


    m = FishAudioMethod()
    res_default = m.run(
        prompt="",
        project=project,
        target_name="sample_default",
        text=text_huzi,
        workdir=workdir,
    )

    print("\n✅ 测试完成！音频已输出到：", workdir / "project" / project / "audio")
    print(json.dumps(res_default, ensure_ascii=False, indent=2))



if __name__ == "__main__":
    try_audio_engine()
