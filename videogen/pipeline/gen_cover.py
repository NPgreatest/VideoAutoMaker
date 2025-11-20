#!/usr/bin/env python3
from __future__ import annotations
import os
import re
from pathlib import Path
from typing import Dict, List
from dacite import from_dict
from dotenv import load_dotenv
import cv2
from PIL import Image, ImageDraw, ImageFont

from videogen.schema.project_schema import ScriptBlock

# ========== 配置项 ==========
load_dotenv()
FONT_PATH = os.getenv("FONT_PATH")


# ============================================================
# 🔧 兼容 Pillow 新旧版本的文本测量函数（textbbox / textsize）
# ============================================================
def measure_text(draw: ImageDraw.Draw, text: str, font: ImageFont.ImageFont):
    """兼容 Pillow 新旧版本的文本测量函数"""
    if hasattr(draw, "textbbox"):
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]
    else:
        # Pillow < 10
        return draw.textsize(text, font=font)


def gen_cover(project_dir: Path, project_name: str, raw: Dict, blocks: List[ScriptBlock]) -> bool:
    """
    从 _work/norm 目录中随机选 5 个视频，
    在每个视频的 30%–80% 范围内随机抽一帧作为封面。
    """
    try:
        project_title = raw.get("project", project_name)

        match = re.match(r'【([^】]+)】(.*)', project_title)
        if match:
            character_text = match.group(1).strip()
            title_text = match.group(2).strip()
        else:
            character_text = ""
            title_text = project_title

        # 找到 norm 目录
        norm_dir = project_dir / "_work" / "norm"
        if not norm_dir.exists():
            print(f"[cover] ⚠️ Norm directory not found: {norm_dir}")
            return False

        # 找到全部视频
        norm_videos = sorted(norm_dir.glob("*.mp4"))
        if not norm_videos:
            print(f"[cover] ⚠️ No video files in {norm_dir}")
            return False

        # 随机取 5 个视频
        import random
        selected_videos = random.sample(norm_videos, min(5, len(norm_videos)))

        print(f"[cover] 🎬 Selected {len(selected_videos)} videos:")
        for v in selected_videos:
            print("   -", v.name)

        # ============================================================
        # 依次处理 5 个视频，每个生成一个封面
        # ============================================================
        idx = 1
        for bgvideo_path in selected_videos:
            print(f"[cover] ▶ Processing: {bgvideo_path}")

            cap = cv2.VideoCapture(str(bgvideo_path))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            if total_frames <= 0:
                print(f"[cover] ❌ Cannot read video: {bgvideo_path}")
                cap.release()
                continue

            # ======================================================================
            # 随机抽取 30%–80% 的随机帧
            # ======================================================================
            start_f = int(total_frames * 0.30)
            end_f = int(total_frames * 0.80)
            random_frame = random.randint(start_f, end_f)

            cap.set(cv2.CAP_PROP_POS_FRAMES, random_frame)
            success, frame = cap.read()
            cap.release()

            if not success:
                print(f"[cover] ❌ Failed to extract frame from {bgvideo_path}")
                continue

            # 将帧转换为 PIL 图像
            canvas = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            original_width, original_height = canvas.size

            # 封面最小分辨率
            min_width = 960
            min_height = 600

            if original_width < min_width or original_height < min_height:
                scale_w = min_width / original_width if original_width < min_width else 1
                scale_h = min_height / original_height if original_height < min_height else 1
                scale_factor = max(scale_w, scale_h)
                new_width = int(original_width * scale_factor)
                new_height = int(original_height * scale_factor)
                canvas = canvas.resize((new_width, new_height), Image.Resampling.LANCZOS)
            else:
                scale_factor = 1.0

            # 字体缩放
            font_scale = max(canvas.width / 720, 1.0)

            draw = ImageDraw.Draw(canvas)

            base_char_size = int(60 * font_scale)
            base_title_size = int(50 * font_scale)

            # 加载字体
            font_character = None
            font_title = None

            if FONT_PATH and Path(FONT_PATH).exists():
                try:
                    font_character = ImageFont.truetype(FONT_PATH, base_char_size)
                    font_title = ImageFont.truetype(FONT_PATH, base_title_size)
                except:
                    pass

            if not font_character:
                fallback = Path("assets/microhei.ttc")
                if fallback.exists():
                    font_character = ImageFont.truetype(str(fallback), base_char_size)
                    font_title = ImageFont.truetype(str(fallback), base_title_size)

            if not font_character:
                font_character = ImageFont.load_default()
                font_title = ImageFont.load_default()

            # 文本尺寸
            if character_text:
                w_c, h_c = measure_text(draw, character_text, font_character)
            else:
                w_c = h_c = 0

            # 处理标题B部分：如果超过12个字，自动换行
            # 注意：title_text 是【A】B格式中的B部分，只对B部分进行换行处理
            title_lines = []
            if title_text:
                if len(title_text) > 12:
                    # 每行最多12个字，按12个字切分
                    for i in range(0, len(title_text), 12):
                        title_lines.append(title_text[i:i+12])
                else:
                    title_lines = [title_text]
            else:
                title_lines = []

            # 计算标题每行的尺寸和总高度
            title_line_info = []  # [(width, height), ...]
            title_total_height = 0
            if title_lines:
                for line in title_lines:
                    w_t, h_t = measure_text(draw, line, font_title)
                    title_line_info.append((w_t, h_t))
                    title_total_height += h_t
                # 添加行间距（行高的一半）
                if len(title_lines) > 1:
                    line_spacing = int(title_line_info[0][1] * 0.5)
                    title_total_height += line_spacing * (len(title_lines) - 1)

            stroke_width = max(4, int(4 * font_scale))

            # 绘制角色文字
            if character_text:
                x_c = (canvas.width - w_c) // 2
                y_c = (canvas.height - h_c) // 2 + int(300 * font_scale)
                draw.text(
                    (x_c, y_c),
                    character_text,
                    font=font_character,
                    fill=(255, 255, 255),
                    stroke_width=stroke_width,
                    stroke_fill="black",
                )

            # 绘制标题文字（支持多行，靠右下方显示，避免遮挡人脸）
            if title_lines:
                # 向右偏移量（避免遮挡左侧人脸）
                x_offset_right = int(100 * font_scale)  # 向右偏移
                
                # 计算起始Y坐标（从底部向上，但更靠下）
                y_bottom = canvas.height - int(80 * font_scale)  # 减少底部边距，让文字更靠下
                y_start = y_bottom - title_total_height
                
                # 行间距
                line_spacing = int(title_line_info[0][1] * 0.5) if len(title_lines) > 1 else 0
                
                # 逐行绘制（靠右对齐）
                current_y = y_start
                for line_idx, line in enumerate(title_lines):
                    w_t, h_t = title_line_info[line_idx]
                    # 靠右对齐，并向右偏移
                    x_t = canvas.width - w_t - x_offset_right
                    
                    draw.text(
                        (x_t, current_y),
                        line,
                        font=font_title,
                        fill=(255, 255, 0),
                        stroke_width=stroke_width,
                        stroke_fill="black",
                    )
                    # 移动到下一行
                    current_y += h_t + line_spacing

            # 输出文件
            output_path = project_dir / f"{project_name}_cover_{idx}.jpg"
            canvas.save(output_path, quality=95)
            print(f"[cover] ✅ Saved cover: {output_path}")

            idx += 1

        return True

    except Exception as e:
        print(f"[cover] ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    load_dotenv()
    project_name = os.getenv("PROJECT_NAME")

    if not project_name:
        raise SystemExit("Please set PROJECT_NAME in .env file")

    project_dir = Path(f"project/{project_name}")
    json_path = project_dir / f"{project_name}.json"

    if not json_path.exists():
        raise SystemExit(f"Project JSON not found: {json_path}")

    from videogen.pipeline.utils import read_json

    raw = read_json(json_path)

    blocks = [from_dict(ScriptBlock, b) for b in raw.get("script", [])]

    print(f"🎨 Generating cover for project: {project_name}")
    success = gen_cover(project_dir, project_name, raw, blocks)

    if success:
        print("✅ Cover generation completed!")
    else:
        print("❌ Cover generation failed!")
        exit(1)
