#!/usr/bin/env python3
from __future__ import annotations

from google import genai
from google.genai.types import GenerateImagesConfig

from wiki2video.config.config_manager import config

client = genai.Client(
    vertexai=True,
    project=config.get("google", "project_id"),
)


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
    """
    使用 Google Vertex AI Imagen 生成图片并返回原始图片字节。
    
    Args:
        prompt: 图片生成提示词
        negative_prompt: 负面提示词（Google Imagen 可能不支持，会被忽略）
        size: 图片尺寸，如 "1280x720" 或 "1024x1024"
    
    Returns:
        图片的原始字节数据
    
    Raises:
        ValueError: 如果配置缺失或生成失败
        RuntimeError: 如果生成过程中出现错误
    """
    project_id = config.get("google", "project_id")
    if not project_id:
        raise ValueError("Missing google.project_id in config.json")
    
    # 映射尺寸格式
    image_size = _map_size_to_google_format(size)
    
    # 构建配置
    # 注意：Google Imagen 可能不支持 negative_prompt，所以暂时不包含
    config_obj = GenerateImagesConfig(
        aspect_ratio= image_size, #"16:9" or 0:16
        image_size="2K",
    )
    
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

