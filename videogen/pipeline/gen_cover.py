#!/usr/bin/env python3
from __future__ import annotations
import os
import re
from pathlib import Path
from typing import Dict, List, Optional
from dacite import from_dict
from dotenv import load_dotenv
import cv2
from PIL import Image, ImageDraw, ImageFont
from videogen.pipeline.schema import ScriptBlock

# ========== 配置项 ==========
load_dotenv()
FONT_PATH = os.getenv("FONT_PATH")


def gen_cover(project_dir: Path, project_name: str, raw: Dict, blocks: List[ScriptBlock]) -> bool:
    """
    生成项目的封面照片。
    
    封面使用 _work/norm/*.mp4 的第一帧作为背景。
    项目名称格式：【角色名】标题
    - 【】里面的内容放在屏幕中间偏下，白色
    - 后面的标题以黄色放在字幕位置（底部往上）
    
    Args:
        project_dir: 项目目录
        project_name: 项目名称
        raw: 项目 JSON 数据
        blocks: 脚本块列表
    
    Returns:
        是否成功生成封面
    """
    try:
        # 从项目名称中提取标题
        project_title = raw.get("project", project_name)
        
        # 匹配格式：【角色名】标题
        match = re.match(r'【([^】]+)】(.*)', project_title)
        
        if match:
            # 【】里面的内容（角色名）
            character_text = match.group(1).strip()
            # 后面的标题
            title_text = match.group(2).strip()
        else:
            # 如果没有【】格式，使用项目名称作为标题，角色为空
            character_text = ""
            title_text = project_title
        
        # 输出路径
        output_path = project_dir / f"{project_name}.jpg"
        
        # 获取 _work/norm 目录下的第一个 mp4 文件作为背景
        norm_dir = project_dir / "_work" / "norm"
        
        if not norm_dir.exists():
            print(f"[cover] ⚠️ Norm directory not found: {norm_dir}, skipping cover generation.")
            return False
        
        # 查找所有 mp4 文件，按名称排序，取第一个
        norm_videos = sorted(norm_dir.glob("*.mp4"))
        
        if not norm_videos:
            print(f"[cover] ⚠️ No video files found in {norm_dir}, skipping cover generation.")
            return False
        
        bgvideo_path = norm_videos[0]
        print(f"[cover] 🖼️ Generating cover image...")
        print(f"[cover] Character text: {character_text}")
        print(f"[cover] Title text: {title_text}")
        print(f"[cover] Background video: {bgvideo_path}")
        
        # 从视频中提取第一帧
        cap = cv2.VideoCapture(str(bgvideo_path))
        success, frame = cap.read()
        cap.release()
        
        if not success:
            print(f"[cover] ❌ Failed to extract frame from video")
            return False
        
        # 将提取的帧转换为PIL图像
        canvas = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        original_width, original_height = canvas.size
        print(f"[cover] Original frame size: {original_width}x{original_height}")

        # 确保封面分辨率至少为 960x600
        min_width = 960
        min_height = 600
        resize_needed = False
        scale_factor = 1.0

        if original_width < min_width or original_height < min_height:
            scale_w = min_width / original_width if original_width < min_width else 1.0
            scale_h = min_height / original_height if original_height < min_height else 1.0
            scale_factor = max(scale_w, scale_h)
            new_width = int(round(original_width * scale_factor))
            new_height = int(round(original_height * scale_factor))
            new_width = max(new_width, min_width)
            new_height = max(new_height, min_height)
            resize_needed = True
            print(f"[cover] Upscaling canvas to {new_width}x{new_height} (scale={scale_factor:.2f})")

            try:
                canvas = canvas.resize((new_width, new_height), Image.Resampling.LANCZOS)
            except AttributeError:
                canvas = canvas.resize((new_width, new_height), Image.LANCZOS)
        else:
            print("[cover] Canvas already meets minimum resolution.")

        # 字体及位置缩放系数基于缩放后的画布宽度（相对于 720px 基准）
        base_width = 720.0
        font_scale = canvas.width / base_width
        font_scale = max(font_scale, 1.0)  # 不缩小字体，只放大
        print(f"[cover] Font scale factor: {font_scale:.2f}")

        draw = ImageDraw.Draw(canvas)
        
        # 根据缩放系数计算字体大小
        base_char_size = max(60, int(round(60 * font_scale)))
        base_title_size = max(50, int(round(50 * font_scale)))

        # 尝试加载字体，如果失败则使用默认字体
        font_character = None
        font_title = None
        
        # 尝试使用 FONT_PATH 环境变量指定的字体（加粗版本）
        if FONT_PATH and Path(FONT_PATH).exists():
            try:
                # 尝试加载粗体字体，如果失败则使用普通字体
                font_character = ImageFont.truetype(FONT_PATH, base_char_size)
                font_title = ImageFont.truetype(FONT_PATH, base_title_size)
            except Exception as e:
                print(f"[cover] ⚠️ Failed to load font from FONT_PATH: {e}")
        
        # 如果 FONT_PATH 失败，尝试使用 assets/microhei.ttc
        if not font_character:
            default_font_path = Path("assets/microhei.ttc")
            if default_font_path.exists():
                try:
                    font_character = ImageFont.truetype(str(default_font_path), base_char_size)
                    font_title = ImageFont.truetype(str(default_font_path), base_title_size)
                except Exception as e:
                    print(f"[cover] ⚠️ Failed to load default font: {e}")
        
        # 如果还是失败，使用默认字体
        if not font_character:
            try:
                font_character = ImageFont.truetype("arial.ttf", base_char_size)
                font_title = ImageFont.truetype("arial.ttf", base_title_size)
            except:
                font_character = ImageFont.load_default()
                font_title = ImageFont.load_default()
        
        # 计算文字位置
        # 使用 textbbox 替代已废弃的 textsize
        if hasattr(draw, 'textbbox'):
            # 计算角色文字（【】里面的内容）尺寸
            if character_text:
                bbox_character = draw.textbbox((0, 0), character_text, font=font_character)
                w_character = bbox_character[2] - bbox_character[0]
                h_character = bbox_character[3] - bbox_character[1]
            else:
                w_character = h_character = 0
            
            # 计算标题文字尺寸
            if title_text:
                bbox_title = draw.textbbox((0, 0), title_text, font=font_title)
                w_title = bbox_title[2] - bbox_title[0]
                h_title = bbox_title[3] - bbox_title[1]
            else:
                w_title = h_title = 0
        else:
            # 兼容旧版本 PIL
            if character_text:
                w_character, h_character = draw.textsize(character_text, font=font_character)
            else:
                w_character = h_character = 0
            
            if title_text:
                w_title, h_title = draw.textsize(title_text, font=font_title)
            else:
                w_title = h_title = 0
        
        # 计算文字位置
        offset_character_y = int(round(300 * font_scale))
        offset_title_y = int(round(150 * font_scale))
        stroke_width = max(4, int(round(4 * font_scale)))

        # 角色文字：屏幕中间偏下
        if character_text:
            x_character = (canvas.width - w_character) // 2
            y_character = (canvas.height - h_character) // 2 + offset_character_y
            
            draw.text(
                (x_character, y_character),
                character_text,
                font=font_character,
                fill=(255, 255, 255, 255),
                stroke_width=stroke_width,
                stroke_fill="black",
            )
        
        # 标题文字：字幕位置（底部往上）
        if title_text:
            x_title = (canvas.width - w_title) // 2
            y_title = canvas.height - h_title - offset_title_y
            
            draw.text(
                (x_title, y_title),
                title_text,
                font=font_title,
                fill=(255, 255, 0, 255),
                stroke_width=stroke_width,
                stroke_fill="black",
            )
        
        # 保存最终图片（已经是 RGB 模式）
        canvas.save(output_path, quality=95)
        
        print(f"[cover] ✅ Cover image saved to: {output_path}")
        return True
        
    except Exception as e:
        print(f"[cover] ❌ Failed to generate cover image: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # 调试模式：从环境变量读取项目名
    load_dotenv()
    project_name = os.getenv("PROJECT_NAME")
    
    if not project_name:
        raise SystemExit("Please set PROJECT_NAME in .env file")
    
    project_dir = Path(f"project/{project_name}")
    json_path = project_dir / f"{project_name}.json"
    
    if not json_path.exists():
        raise SystemExit(f"Project JSON not found: {json_path}")
    
    # 读取项目 JSON
    from videogen.pipeline.utils import read_json
    raw = read_json(json_path)
    
    # 解析 blocks
    blocks = [from_dict(ScriptBlock, b) for b in raw.get("script", [])]
    
    # 生成封面
    print(f"🎨 Generating cover for project: {project_name}")
    success = gen_cover(project_dir, project_name, raw, blocks)
    
    if success:
        print("✅ Cover generation completed!")
    else:
        print("❌ Cover generation failed!")
        exit(1)

