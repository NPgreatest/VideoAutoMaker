# videogen/router/decider.py
from __future__ import annotations
from typing import Optional
from wiki2video.llm_engine import get_engine

def decide_generation_method(
    text: str,
    topic: str,
    context: Optional[str] = None,
) -> str:
    """
    调用 LLM，判断该台词应使用哪种生成方式：
    - react_animation
    - text_to_image
    - subtitle_only
    """

    engine = get_engine()

    # Prompt 模板写在这里，而不是 LLMEngine
    system_prompt = (
        "You are a smart video director assistant that decides which rendering method best fits a given line of script.\n"
        "You must always choose one of the following options:\n"
        "1. react_animation — use this when the line contains numbers, quantities, statistics, comparisons, or structured information "
        "(e.g., counts of people, timelines, lists, flight paths, or any data that can be visualized with charts, icons, or infographics using react front-end).\n"
        "2. text_video — use this when the line describes a vivid scene, action, or environment that can be represented visually, "
        "such as locations, objects, weather, or cinematic imagery.\n"
        # "3. subtitle_only — use this when the line focuses mainly on narration, thoughts, quotes, or emotional commentary, "
        # "where no specific visual representation is required.\n"
        "Be especially careful: when the line involves numeric or structured details (like flight numbers, passenger counts, or maps), "
        "prefer react_animation over text_to_image.\n"
        "Respond with only one keyword: react_animation, text_to_image, or subtitle_only."
    )

    user_prompt = (
        f"Video topic: {topic}\n\n"
        f"Line: {text}\n"
    )

    if context:
        user_prompt += f"\nContext: {context}\n"

    user_prompt += "\nWhich rendering method should be used? Reply with one keyword only."

    res = engine.chat(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=20,
    )

    method = res["content"].strip().lower()
    # normalize output
    if "remotion" in method:
        return "remotion_picture"
    elif "image" in method or "picture" or "video" in method:
        return "text_video"
    else:
        return "text_video"
