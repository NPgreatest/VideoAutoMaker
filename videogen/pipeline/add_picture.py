#!/usr/bin/env python3
from __future__ import annotations
import os
import subprocess
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# ========== 配置项 ==========
load_dotenv()

# 从 .env 读取图片配置，如果没有则使用默认值
PICTURE_PATH = os.getenv("PICTURE_PATH", "./assets/pic/huchenfeng.png")
PICTURE_WIDTH = int(os.getenv("PICTURE_WIDTH", "200"))  # 图片宽度（像素）
PICTURE_HEIGHT = int(os.getenv("PICTURE_HEIGHT", "200"))  # 图片高度（像素）
PICTURE_X = int(os.getenv("PICTURE_X", "20"))  # 距离左边的距离（像素）
PICTURE_Y = int(os.getenv("PICTURE_Y", "-1"))  # -1 表示底部，或指定距离顶部的距离（像素）

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

# ========== 主函数 ==========
def add_picture_overlay(
    video_path: Path,
    output_path: Path,
    picture_path: Optional[Path] = None,
    picture_width: Optional[int] = None,
    picture_height: Optional[int] = None,
    picture_x: Optional[int] = None,
    picture_y: Optional[int] = None
) -> bool:
    """
    在视频上叠加图片，图片位于底部左侧
    
    层级关系：视频层 < 图片层 < 字幕层（字幕由后续步骤添加）
    
    Args:
        video_path: 输入视频路径
        output_path: 输出视频路径
        picture_path: 图片路径（如果为 None，则从 .env 读取）
        picture_width: 图片宽度（如果为 None，则从 .env 读取）
        picture_height: 图片高度（如果为 None，则从 .env 读取）
        picture_x: 图片 X 坐标（如果为 None，则从 .env 读取）
        picture_y: 图片 Y 坐标（如果为 None，则从 .env 读取，-1 表示底部）
    
    Returns:
        成功返回 True，失败返回 False
    """
    # 使用参数或从环境变量读取
    if picture_path:
        pic_path = Path(picture_path)
    else:
        # 处理相对路径，从项目根目录解析
        pic_path = Path(PICTURE_PATH)
        if not pic_path.is_absolute():
            # 如果是相对路径，从项目根目录解析（假设在项目根目录运行）
            project_root = Path.cwd()
            pic_path = (project_root / pic_path).resolve()
    pic_w = picture_width if picture_width is not None else PICTURE_WIDTH
    pic_h = picture_height if picture_height is not None else PICTURE_HEIGHT
    pic_x = picture_x if picture_x is not None else PICTURE_X
    pic_y = picture_y if picture_y is not None else PICTURE_Y
    
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
    
    # 计算 Y 坐标（如果为 -1，则放在底部）
    if pic_y == -1:
        pic_y = video_h - pic_h - 20  # 距离底部 20 像素
    
    # 构建 ffmpeg filter_complex
    # 1. 缩放图片到指定大小
    # 2. 将缩放后的图片叠加到视频上
    # 格式：[1:v]scale=w:h[scaled];[0:v][scaled]overlay=x:y[outv]
    scale_filter = f"[1:v]scale={pic_w}:{pic_h}[scaled]"
    overlay_filter = f"[0:v][scaled]overlay={pic_x}:{pic_y}[outv]"
    filter_complex = f"{scale_filter};{overlay_filter}"
    
    # 构建 ffmpeg 命令
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),  # 输入视频
        "-i", str(pic_path),    # 输入图片
        "-filter_complex", filter_complex,
        "-map", "[outv]",  # 映射视频流（来自 filter_complex 的输出）
        "-c:v", "libx264",
        "-preset", PRESET,
        "-crf", CRF,
        "-pix_fmt", PIX_FMT,
    ]
    
    # 如果有音频流，添加音频映射和编码参数
    if has_audio:
        cmd.extend(["-map", "0:a", "-c:a", "copy"])  # 复制音频流
    
    cmd.append(str(output_path))
    
    print(f"[picture] 🖼️  Adding picture overlay to video...")
    print(f"[picture]    Picture: {pic_path}")
    print(f"[picture]    Size: {pic_w}x{pic_h}")
    print(f"[picture]    Position: ({pic_x}, {pic_y})")
    
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

