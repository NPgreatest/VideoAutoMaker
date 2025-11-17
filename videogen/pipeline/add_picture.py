#!/usr/bin/env python3
from __future__ import annotations
import os
import subprocess
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# ========== 配置项 ==========
load_dotenv()

# 使用比例模式：相对于视频尺寸的比例（0.0-1.0）
# 例如 0.15 表示视频宽度的 15%，高度会根据图片原始宽高比自动计算
PICTURE_WIDTH_RATIO = float(os.getenv("PICTURE_WIDTH_RATIO", "0.15"))  # 图片宽度比例（相对于视频宽度，高度自动保持宽高比）
PICTURE_X_RATIO = float(os.getenv("PICTURE_X_RATIO", "0.02"))  # X坐标比例（相对于视频宽度，可以为负值让图片部分移出屏幕左侧）
PICTURE_Y_RATIO = float(os.getenv("PICTURE_Y_RATIO", "-1"))  # -1 表示底部，或指定距离顶部的比例（相对于视频高度）
# 底部边距比例（当 PICTURE_Y_RATIO 为 -1 时使用）
PICTURE_BOTTOM_MARGIN_RATIO = float(os.getenv("PICTURE_BOTTOM_MARGIN_RATIO", "0.02"))  # 距离底部的比例

# 视频编码参数（与 concat.py 保持一致）
CRF = "14"
PRESET = "slow"
PIX_FMT = "yuv420p"

# ========== 辅助函数 ==========
def run(cmd: list[str]) -> bool:
    """运行 ffmpeg 命令"""
    print(f"[ffmpeg] {' '.join(cmd)}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(proc.stderr[-400:])
        return False
    return True

def ffprobe(path: Path) -> dict:
    """获取视频信息"""
    cmd = ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-print_format", "json", str(path)]
    out = subprocess.check_output(cmd, text=True)
    import json
    return json.loads(out)

def get_image_dimensions(image_path: Path) -> tuple[int, int]:
    """获取图片的原始尺寸（宽，高）"""
    try:
        # 使用 ffprobe 获取图片尺寸（支持更多格式）
        cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", 
               "-show_entries", "stream=width,height", 
               "-of", "json", str(image_path)]
        out = subprocess.check_output(cmd, text=True)
        import json
        data = json.loads(out)
        if "streams" in data and len(data["streams"]) > 0:
            stream = data["streams"][0]
            return int(stream["width"]), int(stream["height"])
    except Exception as e:
        print(f"[picture] ⚠️  Failed to get image dimensions with ffprobe: {e}")
    
    # 回退到 PIL
    try:
        from PIL import Image
        with Image.open(image_path) as img:
            return img.size  # (width, height)
    except Exception as e:
        print(f"[picture] ❌ Failed to get image dimensions: {e}")
        # 返回默认值
        return 1, 1

# ========== 主函数 ==========
def add_picture_overlay(
    video_path: Path,
    output_path: Path,
    picture_path: Optional[Path] = None,
    picture_width: Optional[float] = None,
    picture_x: Optional[float] = None,
    picture_y: Optional[float] = None
) -> bool:
    """
    在视频上叠加图片，图片位于底部左侧（使用比例模式，保持原始宽高比）
    
    层级关系：视频层 < 图片层 < 字幕层（字幕由后续步骤添加）
    
    Args:
        video_path: 输入视频路径
        output_path: 输出视频路径
        picture_path: 图片路径（如果为 None，则从 .env 读取）
        picture_width: 图片宽度比例（0.0-1.0，相对于视频宽度，高度会根据图片原始宽高比自动计算，如果为 None，则从 .env 读取）
        picture_x: 图片 X 坐标比例（可以为负值，相对于视频宽度，如果为 None，则从 .env 读取。负值可以让图片部分移出屏幕左侧）
        picture_y: 图片 Y 坐标比例（0.0-1.0，相对于视频高度，-1 表示底部，如果为 None，则从 .env 读取）
    
    Returns:
        成功返回 True，失败返回 False
    """
    pic_path = Path(picture_path)
    
    # 检查文件是否存在
    if not video_path.exists():
        print(f"[picture] ❌ Video file not found: {video_path}")
        return False
    
    if not pic_path.exists():
        print(f"[picture] ❌ Picture file not found: {pic_path}")
        return False
    
    # 获取视频尺寸和音频信息
    video_info = ffprobe(video_path)
    video_stream = next(s for s in video_info["streams"] if s["codec_type"] == "video")
    audio_streams = [s for s in video_info["streams"] if s["codec_type"] == "audio"]
    has_audio = len(audio_streams) > 0
    video_w = int(video_stream["width"])
    video_h = int(video_stream["height"])
    
    # 获取图片原始尺寸
    pic_orig_w, pic_orig_h = get_image_dimensions(pic_path)
    pic_aspect_ratio = pic_orig_w / pic_orig_h if pic_orig_h > 0 else 1.0
    
    # 使用比例模式计算图片大小和位置
    width_ratio = picture_width if picture_width is not None else PICTURE_WIDTH_RATIO
    x_ratio = picture_x if picture_x is not None else PICTURE_X_RATIO
    y_ratio = picture_y if picture_y is not None else PICTURE_Y_RATIO
    
    # 根据视频宽度比例计算图片宽度，然后根据图片原始宽高比计算高度
    pic_w = int(video_w * width_ratio)
    pic_h = int(pic_w / pic_aspect_ratio)  # 保持原始宽高比
    # X坐标可以是负数，让图片部分移出屏幕左侧
    pic_x = int(video_w * x_ratio)
    
    # 计算 Y 坐标（如果为 -1，则放在底部）
    if y_ratio == -1:
        # 使用底部边距比例
        bottom_margin = int(video_h * PICTURE_BOTTOM_MARGIN_RATIO)
        pic_y = video_h - pic_h - bottom_margin
    else:
        pic_y = int(video_h * y_ratio)
    
    # 构建 ffmpeg filter_complex
    # 1. 缩放图片到指定宽度，高度自动保持宽高比（使用 -1）
    # 2. 将缩放后的图片叠加到视频上
    # 格式：[1:v]scale=w:-1[scaled];[0:v][scaled]overlay=x:y[outv]
    # Note: 图片作为第二个输入，需要先转换为视频流
    # 使用 scale=w:-1 让 ffmpeg 自动计算高度以保持宽高比
    scale_filter = f"[1:v]scale={pic_w}:-1[scaled]"
    overlay_filter = f"[0:v][scaled]overlay={pic_x}:{pic_y}[outv]"
    filter_complex = f"{scale_filter};{overlay_filter}"
    
    # 构建 ffmpeg 命令
    # 使用 -loop 1 让图片作为视频流输入，确保图片可以正确叠加
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),  # 输入视频 (input 0)
        "-loop", "1", "-i", str(pic_path),  # 输入图片作为视频流 (input 1)
        "-filter_complex", filter_complex,
        "-map", "[outv]",  # 映射视频流（来自 filter_complex 的输出）
        "-c:v", "libx264",
        "-preset", PRESET,
        "-crf", CRF,
        "-pix_fmt", PIX_FMT,
        "-shortest",  # 确保输出长度与视频一致
    ]
    
    # 如果有音频流，添加音频映射和编码参数
    # Explicitly map the first audio stream to avoid issues with multiple audio streams
    if has_audio:
        cmd.extend(["-map", "0:a:0", "-c:a", "copy"])  # 复制第一个音频流
    
    cmd.append(str(output_path))
    
    print(f"[picture] 🖼️  Adding picture overlay to video...")
    print(f"[picture]    Picture: {pic_path}")
    print(f"[picture]    Original picture size: {pic_orig_w}x{pic_orig_h} (aspect ratio: {pic_aspect_ratio:.2f})")
    print(f"[picture]    Video size: {video_w}x{video_h}")
    print(f"[picture]    Scaled picture size: {pic_w}x{pic_h} (width ratio: {width_ratio:.2%}, maintaining aspect ratio)")
    print(f"[picture]    Position: ({pic_x}, {pic_y}) (ratio: {x_ratio:.2%}, {y_ratio if y_ratio != -1 else 'bottom'})")
    
    ok = run(cmd)
    if ok:
        print(f"[picture] ✅ Picture overlay added: {output_path}")
    else:
        print(f"[picture] ❌ Failed to add picture overlay")
    
    return ok


# ========== 入口（用于测试）==========
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python add_picture.py <input_video> <output_video>")
        sys.exit(1)
    
    load_dotenv()
    input_video = Path(sys.argv[1])
    output_video = Path(sys.argv[2])
    
    success = add_picture_overlay(input_video, output_video)
    sys.exit(0 if success else 1)

