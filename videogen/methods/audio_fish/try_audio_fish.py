#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from videogen.methods.audio_fish.method import FishAudioMethod
from videogen.schema.schema import ScriptBlock


def try_audio_engine():
    """测试 SiliconAudioMethod，生成默认角色和 Mark 角色的两段音频。"""
    workdir = Path("_test_out").resolve()
    project = "audio_demo_fish"

    # ===================== 测试文本 =====================
    text_huzi = (
        "所以我说啊，没朋友不是悲哀，是你终于学会了，谁值得留在生命里。"
    )


    m = FishAudioMethod()
    res_default = m.run(
        project=project,
        target_name="fish_audio_default",
        text=text_huzi,
        workdir=workdir,
        block=ScriptBlock(character="huchenfeng",id="L1",text=text_huzi),
    )

    print("\n✅ 测试完成！音频已输出到：", workdir / "project" / project / "audio")
    print(json.dumps(res_default, ensure_ascii=False, indent=2))



if __name__ == "__main__":
    try_audio_engine()
