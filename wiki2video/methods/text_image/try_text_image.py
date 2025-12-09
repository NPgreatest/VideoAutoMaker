#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from wiki2video.methods.text_image.method import TextImageMethod
from wiki2video.methods.text_image.schema import TextImageConfig
from wiki2video.schema.action_spec import ActionSpec


def main():
    """
    Simple CLI helper that exercises TextImageMethod end-to-end.
    """

    demo_dir = Path("_text_image_demo").resolve()
    demo_config = TextImageConfig(
        prompt="A cinematic aerial shot of an ancient underground city illuminated by torches.",
        negative_prompt="low quality, distorted, blurry",
        size="1024x1024",
        workdir=str(demo_dir),
        target_name="demo_block",
    )

    method = TextImageMethod()
    action = ActionSpec(type=method.NAME, config=demo_config.model_dump())
    wb = method.run(action)
    poll_result = method.poll(wb)

    print("✅ TextImageMethod finished. Output:")
    print(json.dumps({
        "status": poll_result.status.value,
        "image_path": poll_result.output_path,
        "error": poll_result.error,
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
