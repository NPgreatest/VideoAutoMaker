#!/usr/bin/env python3
from __future__ import annotations

from wiki2video.config.config_manager import config


def _map_size_to_google_format(size: str) -> str:
    try:
        if "x" in size:
            width, height = map(int, size.split("x"))
            if width == 1280 and height == 720:
                return "16:9"
            elif width == 720 and height == 1280:
                return "9:16"
            else:
                return "1:1"
        else:
            return "1:1"
    except (ValueError, AttributeError):
        # 解析失败，使用默认值
        return "1:1"


def google_generate_image(
    prompt: str,
    negative_prompt: str | None,
    size: str,
) -> bytes:
    try:
        from google import genai
    except ImportError:
        raise RuntimeError(
            "Google support is not installed.\n"
            "Install it with:\n\n"
            "  pip install 'wiki2video[google]'"
        )

    project_id = config.get("google", "project_id")
    if not project_id:
        raise ValueError("Missing google.project_id in config.json")

    client = genai.Client(
        vertexai=True,
        project=project_id,
    )
    
    # 映射尺寸格式
    image_size = _map_size_to_google_format(size)
    
    # 构建配置
    # 注意：Google Imagen 可能不支持 negative_prompt，所以暂时不包含
    config_obj = {
    "aspect_ratio": image_size,
    "image_size": "2K",
    }

    print(f"Generating image with config_obj: {config_obj}")
    try:
        # 调用 Google Imagen API
        image_response = client.models.generate_images(
            model="imagen-4.0-generate-001",
            prompt=prompt,
            config=config_obj,
        )
        
        # 检查响应
        if not image_response.generated_images:
            raise RuntimeError("Google Imagen returned no images")
        
        # 获取第一张图片的字节数据
        image_bytes = image_response.generated_images[0].image.image_bytes
        
        if not image_bytes:
            raise RuntimeError("Google Imagen returned empty image bytes")
        
        return image_bytes
        
    except Exception as e:
        raise RuntimeError(f"Google Imagen generation failed: {e}") from e


__all__ = ["google_generate_image"]

