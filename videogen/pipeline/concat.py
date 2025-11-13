#!/usr/bin/env python3
from __future__ import annotations
import os, json, re, subprocess, shutil
from pathlib import Path
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from dacite import from_dict
from dotenv import load_dotenv
from videogen.pipeline.schema import ScriptBlock
from videogen.pipeline.utils import read_json, write_json, get_character_info, set_project_status
from videogen.pipeline.schema import ProjectStatus
from videogen.pipeline.add_picture import add_picture_overlay
from videogen.pipeline.gen_cover import gen_cover

# ========== 配置项 ==========
CRF = "14"             # 画质（越低越好）
PRESET = "slow"
AUDIO_RATE = "44100"
AUDIO_BR = "192k"
PIX_FMT = "yuv420p"

load_dotenv()
BGM_PATH = os.getenv("BGM_PATH")
FONT_PATH = os.getenv("FONT_PATH")


# ========== 辅助函数 ==========
def run(cmd: List[str]) -> bool:
    print(f"[ffmpeg] {' '.join(cmd)}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(proc.stderr[-400:])
        return False
    return True

def ffprobe(path: Path) -> Dict:
    cmd = ["ffprobe","-v","error","-show_streams","-show_format","-print_format","json",str(path)]
    out = subprocess.check_output(cmd, text=True)
    return json.loads(out)

def parse_fps(s: str) -> float:
    if not s or s=="0/0": return 30
    n,d = map(float, s.split("/")) if "/" in s else (float(s),1)
    return n/d

@dataclass
class ClipInfo:
    path: Path
    w: int
    h: int
    fps: float
    has_audio: bool

def get_clip_info(p: Path) -> ClipInfo:
    d = ffprobe(p)
    v = next(s for s in d["streams"] if s["codec_type"]=="video")
    a = [s for s in d["streams"] if s["codec_type"]=="audio"]
    w,h = int(v["width"]), int(v["height"])
    fps = parse_fps(v.get("r_frame_rate") or v.get("avg_frame_rate"))
    return ClipInfo(p,w,h,fps,bool(a))

# ========== 阶段 1：收集并补齐 muxed ==========
def ensure_muxed(project_dir: Path, idx: int, muxed_dir: Path, block: Optional[ScriptBlock] = None) -> Optional[Path]:
    # Check and generate in muxed_dir
    mux = muxed_dir / f"L{idx}_muxed.mp4"
    if mux.exists(): return mux
    
    # Check remotion_video folder first (stores raw videos like video folder)
    video = project_dir / "remotion_video" / f"L{idx}.mp4"
    if not video.exists():
        # Fallback to video/ subdirectory, then project root
        video = project_dir / "video" / f"L{idx}.mp4"
        if not video.exists():
            video = project_dir / f"L{idx}.mp4"
    
    audio = project_dir / f"audio/L{idx}.wav"
    
    if video.exists() and audio.exists():
        # Resize video to match audio duration if block metadata is available
        resized_video = video
        if block and block.audio_generation:
            audio_gen = block.audio_generation
            if hasattr(audio_gen, 'ok') and audio_gen.ok:
                # It's a GenerationResult object
                target_dur_ms = audio_gen.meta.get('total_duration', None)
            elif isinstance(audio_gen, dict) and audio_gen.get('ok', False):
                # It's a dictionary
                target_dur_ms = audio_gen.get('meta', {}).get('total_duration', None)
            else:
                target_dur_ms = None
            
            if target_dur_ms:
                target_dur_sec = target_dur_ms / 1000.0
                # Import resize function
                from videogen.methods.text_video_silicon.utils import resize_video_duration
                
                # Resize video to target duration (store in _work/resized)
                resized_dir = project_dir / "_work" / "resized"
                resized_dir.mkdir(parents=True, exist_ok=True)
                resized_path = resized_dir / f"L{idx}_resized.mp4"
                
                print(f"[resize] Resizing L{idx} to match audio duration ({target_dur_sec:.2f}s)...")
                new_dur = resize_video_duration(video, resized_path, target_dur_sec)
                
                if new_dur > 0:
                    resized_video = resized_path
                    print(f"[resize] ✅ Resized to {new_dur:.2f}s")
                else:
                    print(f"[resize] ⚠️ Resize failed, using original video")
        
        print(f"[mux] Generating L{idx}_muxed.mp4 ...")
        # Explicitly map video from first input and audio from second input
        # This ensures we use the audio from audio folder, not from the video
        ok = run([
            "ffmpeg","-y","-i",str(resized_video),"-i",str(audio),
            "-map","0:v:0","-map","1:a:0",  # Map video from input 0, audio from input 1
            "-c:v","copy","-c:a","aac","-shortest",str(mux)
        ])
        return mux if ok else None
    print(f"[mux] ⚠️ Missing L{idx}.mp4 or .wav, skipping")
    return None

# ========== 阶段 2：选择统一规格 ==========
def choose_target(infos: List[ClipInfo], project_config: Dict = None) -> Tuple[int,int,int]:
    # Check if project has specific format requirements
    if project_config and "size" in project_config:
        size = project_config["size"]
        if size == "tiktok":
            # TikTok format: 720x1280
            return 720, 1280, 30  # Default to 30fps for TikTok
        elif size == "landscape":
            # Landscape format: 1280x720
            return 1280, 720, 30  # Default to 30fps for landscape
    
    # Fallback to original logic
    max_w = max(i.w for i in infos)
    max_h = max(i.h for i in infos)
    counter = Counter(int(round(i.fps)) for i in infos)
    fps = counter.most_common(1)[0][0]
    return max_w, max_h, fps

# ========== 阶段 3：normalize ==========
def normalize_clip(src: Path, dst: Path, w: int, h: int, fps: int) -> bool:
    vf = f"scale={w}:{h}:force_original_aspect_ratio=decrease," \
         f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,fps={fps},format={PIX_FMT}"
    return run([
        "ffmpeg","-y","-fflags","+genpts","-avoid_negative_ts","make_zero",
        "-i",str(src),
        "-vf",vf,
        "-c:v","libx264","-preset",PRESET,"-crf",CRF,
        "-c:a","aac","-ar",AUDIO_RATE,"-b:a",AUDIO_BR,
        "-pix_fmt",PIX_FMT,
        str(dst)
    ])

# ========== 阶段 4：根据 JSON + 视频时长生成字幕 ==========
def get_duration(path: Path) -> float:
    """Return video duration in seconds."""
    data = ffprobe(path)
    fmt = data.get("format", {})
    dur = fmt.get("duration")
    return float(dur) if dur else 0.0

def fmt_time(x: float) -> str:
    h = int(x // 3600)
    m = int((x % 3600) // 60)
    s = int(x % 60)
    ms = int(round((x - int(x)) * 1000))
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def generate_srt_from_json(raw: Dict, clips: List[Path], out_path: Path) -> None:
    """
    Generate SRT file from JSON.
    优先使用 block.meta['segments'] 里的短句字幕，
    否则 fallback 到原有 block.text + clip 时长。
    每个 segment 都会单独显示，时间戳会加上前面所有 clips 的累计时长。
    """
    blocks = [from_dict(ScriptBlock, b) for b in raw.get("script", [])]
    assert len(blocks) == len(clips), f"Script blocks ({len(blocks)}) != clips ({len(clips)})"

    idx = 1
    lines = []
    block_index = 0  # Track current block index for calculating offset

    for block, clip in zip(blocks, clips):
        # 计算当前 block 在整个视频中的起始时间（前面所有 clips 的累计时长）
        block_offset = sum(float(get_duration(c)) for c in clips[:block_index])
        
        # 从 audio_generation.meta.segments 获取 segments
        segments = None
        if block.audio_generation and block.audio_generation.ok:
            audio_meta = block.audio_generation.meta
            if isinstance(audio_meta, dict):
                segments = audio_meta.get("segments")
        
        # 如果 segments 存在，为每个 segment 单独生成字幕
        if segments and isinstance(segments, list) and len(segments) > 0:
            # 每个 segment 单独显示，时间戳加上 block 的偏移量
            for seg in segments:
                # segment 应该是字典格式，包含 start, end, text 字段
                if isinstance(seg, dict):
                    seg_start = seg.get("start", 0.0)
                    seg_end = seg.get("end", 0.0)
                    text = seg.get("text", "").strip()
                else:
                    # 如果不是字典，尝试作为对象访问
                    seg_start = getattr(seg, "start", 0.0)
                    seg_end = getattr(seg, "end", 0.0)
                    text = getattr(seg, "text", "").strip()
                
                # segment 的时间戳是相对于当前 block 的（从 0 开始），需要加上 block_offset
                seg_start = float(seg_start) + block_offset
                seg_end = float(seg_end) + block_offset
                
                if text:
                    lines.append(f"{idx}\n{fmt_time(seg_start)} --> {fmt_time(seg_end)}\n{text}\n\n")
                    idx += 1
            block_index += 1
            continue

        # fallback: 原逻辑（整个 clip 一条字幕）
        dur = get_duration(clip)
        text = (block.text or "").strip()
        if text:
            start = block_offset
            end = start + dur
            lines.append(f"{idx}\n{fmt_time(start)} --> {fmt_time(end)}\n{text}\n\n")
            idx += 1
        block_index += 1

    out_path.write_text("".join(lines), encoding="utf-8")
    print(f"[srt] ✅ generated subtitles with segment support -> {out_path}")



# ========== 阶段 5：拼接 ==========
def concat_videos(files: List[Path], out: Path)->bool:
    tmp = out.parent / "concat_list.txt"
    tmp.write_text("\n".join(f"file '{f.resolve()}'" for f in files),encoding="utf-8")
    ok = run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(tmp),
              "-c","copy","-movflags","+faststart",str(out)])
    if ok: print(f"[concat] ✅ {out}")
    return ok

# ========== 阶段 10：生成封面照片 ==========
# 封面生成功能已移至 videogen.pipeline.gen_cover 模块

# ========== 主函数 ==========
def concat_pipeline(project_name:str):
    project_dir=Path(f"project/{project_name}")
    raw=read_json(project_dir/f"{project_name}.json")
    work=project_dir/"_work"; work.mkdir(exist_ok=True)
    muxed_dir=work/"muxed"; muxed_dir.mkdir(exist_ok=True)
    norm_dir=work/"norm"; norm_dir.mkdir(exist_ok=True)

    # Parse blocks for metadata access
    blocks = [from_dict(ScriptBlock, b) for b in raw.get("script", [])]
    
    clips=[]
    clip_blocks=[]
    for i, block in enumerate(blocks, start=1):
        p=ensure_muxed(project_dir, i, muxed_dir, block)
        if p:
            clips.append(p)
            clip_blocks.append(block)
    if not clips: raise SystemExit("❌ no muxed clips found")

    # ====== 阶段 6：逐段添加图片叠加 ======
    picture_dir = work / "picture"
    picture_dir.mkdir(exist_ok=True)

    clips_with_picture = []
    for clip_path, block in zip(clips, clip_blocks):
        picture_output = picture_dir / f"{clip_path.stem}_picture.mp4"
        character = getattr(block, "character", None)
        picture_path = None

        if character:
            character_info = get_character_info(character)
            if character_info:
                image_path_str = character_info.get("image_path")
                if image_path_str:
                    candidate_path = Path(image_path_str)
                    if not candidate_path.is_absolute():
                        project_root = Path.cwd()
                        candidate_path = (project_root / candidate_path).resolve()
                    picture_path = candidate_path

        print(f"[picture] 🎯 Processing clip {clip_path.name} (character={character})")
        ok = add_picture_overlay(
            clip_path,
            picture_output,
            picture_path=picture_path,
        )
        if ok:
            clips_with_picture.append(picture_output)
        else:
            print(f"[picture] ⚠️ Falling back to original clip without overlay: {clip_path}")
            clips_with_picture.append(clip_path)

    infos=[get_clip_info(p) for p in clips_with_picture]
    w,h,fps=choose_target(infos, raw)
    print(f"[spec] Target {w}x{h}@{fps}fps")

    norm=[]
    for c in clips_with_picture:
        out=norm_dir/f"{c.stem}_norm.mp4"
        if normalize_clip(c,out,w,h,fps): norm.append(out)
    if not norm: raise SystemExit("❌ normalize failed")

    final=work/"final.mp4"
    if not concat_videos(norm,final):
        raise SystemExit("concat failed")

    # Generate and beautify SRT directly -> project_name.srt
    out_srt = work / f"{project_name}.srt"
    # First generate raw SRT to a temp file
    temp_srt = work / "temp_srt.srt"
    generate_srt_from_json(raw, norm, temp_srt)
    # Beautify and save directly to final location
    try:
        from videogen.pipeline.beautify_srt import beautify_srt_at_path
        beautify_srt_at_path(temp_srt, out_srt)
        # Remove temp file
        temp_srt.unlink()
        print(f"[srt] ✅ generated and beautified -> {out_srt}")
    except Exception as e:
        print(f"[srt] ⚠️ beautify failed: {e}")
        # If beautify fails, use the raw SRT
        if temp_srt.exists():
            temp_srt.replace(out_srt)
            print(f"[srt] ✅ generated (raw) -> {out_srt}")
    print("✅ pipeline complete!")

    # ====== 阶段 7：字幕硬烧录 ======
    burn_out = project_dir / f"{project_name}_nobgm.mp4"

    # Check if subtitle burning is enabled (default to True for backward compatibility)
    burn_subtitle = raw.get("burn_subtitle", True)
    
    if not burn_subtitle:
        print("[burn] ⏭️  Subtitle burning is disabled, skipping burn-in step.")
        # If burning is disabled, just copy the final video to burn_out
        try:
            shutil.copy2(final, burn_out)
            print(f"[burn] ✅ Copied video without subtitle burn-in to: {burn_out}")
        except Exception as e:
            print(f"[burn] ❌ Failed to copy video: {e}")
    else:
        refined = work / f"{project_name}.srt"
        chosen_srt = refined if refined.exists() else out_srt

        if not chosen_srt.exists():
            print("[burn] ⚠️ No subtitle file found, skipping burn-in.")
        else:
            srt_path = str(chosen_srt.resolve()).replace("\\", "/")
            font_path_abs = str(Path(FONT_PATH).resolve()).replace("\\", "/") if FONT_PATH else "Arial"

            subtitles_filter = (
                f"subtitles='{srt_path}':"
                f"force_style='FontName={Path(font_path_abs).stem},"
                f"FontSize=20,"
                f"PrimaryColour=&H0000FFFF,"   # 黄色字体
                f"OutlineColour=&H00000000,"   # 黑色描边
                f"BorderStyle=1,Outline=2,Shadow=0,"
                f"Alignment=2,MarginL=40,MarginR=40,MarginV=60'"
            )

            cmd = [
                "ffmpeg", "-y",
                "-i", str(final),
                "-vf", subtitles_filter,
                "-c:v", "libx264", "-preset", PRESET, "-crf", CRF,
                "-pix_fmt", PIX_FMT,
                "-c:a", "copy",
                str(burn_out)
            ]

            print("[burn] 🔥 Burning subtitles into video ...")
            ok = run(cmd)
            if ok:
                print(f"[burn] ✅ Subtitle burned video saved to: {burn_out}")
            else:
                print("[burn] ❌ Burn-in failed.")


    # ====== 阶段 8：添加背景音乐 ======
    # 确定无 BGM 成品：若字幕烧录成功，burn_out 已在项目根目录；
    # 若未烧录（或失败），则将当前 final 复制为 {project_name}_nobgm.mp4
    if not burn_out.exists():
        try:
            shutil.copy2(final, burn_out)
            print(f"[nobgm] ✅ Copied video without BGM to: {burn_out}")
        except Exception as e:
            print(f"[nobgm] ❌ Failed to produce no-BGM output: {e}")

    # BGM 输入以无 BGM 成品为准
    input_video = burn_out if burn_out.exists() else final
    
    # Get BGM path from JSON, fallback to environment variable if not set
    bgm_path_str = raw.get("bgm_path")
    if bgm_path_str:
        # Use BGM path from JSON (relative to project root)
        bgm_path = Path(bgm_path_str)
        if not bgm_path.is_absolute():
            # Resolve relative path from project root
            project_root = Path.cwd()
            bgm_path = (project_root / bgm_path).resolve()
    elif BGM_PATH:
        # Fallback to environment variable for backward compatibility
        bgm_path = Path(BGM_PATH)
    else:
        bgm_path = None
    
    if not bgm_path or not bgm_path.exists():
        if bgm_path_str:
            print(f"[bgm] ⚠️ BGM file not found: {bgm_path}, skipping BGM addition.")
        else:
            print(f"[bgm] ℹ️ No BGM specified in project, skipping BGM addition.")
        final_with_bgm = None
    else:
        # 按新规范：带 BGM 的最终成品输出到项目根目录，命名为 {project_name}.mp4
        final_with_bgm = project_dir / f"{project_name}.mp4"
        video_dur = get_duration(input_video)
        bgm_dur = get_duration(bgm_path)
        
        print(f"[bgm] 🎵 Adding background music...")
        print(f"[bgm] Video duration: {video_dur:.2f}s, BGM duration: {bgm_dur:.2f}s")
        
        # Mix audio: video audio + BGM (BGM volume at 0.3, video audio at 1.0)
        # If BGM is shorter than video, loop it
        if bgm_dur < video_dur:
            # Loop BGM to match video duration
            filter_complex = (
                f"[1:a]aloop=loop=-1:size=2e+09,atrim=0:{video_dur},volume=0.3[bgm];"
                f"[0:a]volume=1.0[va];"
                f"[va][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]"
            )
        else:
            # BGM is longer, trim it to video duration
            filter_complex = (
                f"[1:a]atrim=0:{video_dur},volume=0.3[bgm];"
                f"[0:a]volume=1.0[va];"
                f"[va][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]"
            )
        
        cmd = [
            "ffmpeg", "-y",
            "-i", str(input_video),
            "-i", str(bgm_path),
            "-filter_complex", filter_complex,
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-ar", AUDIO_RATE,
            "-b:a", AUDIO_BR,
            "-shortest",
            str(final_with_bgm)
        ]
        
        ok = run(cmd)
        if ok:
            print(f"[bgm] ✅ Final video with BGM saved to: {final_with_bgm}")
        else:
            print(f"[bgm] ❌ BGM mixing failed.")
            final_with_bgm = None

    # ====== 阶段 10：生成封面照片 ======
    # 使用 _work/norm/*.mp4 的第一帧作为背景
    gen_cover(project_dir, project_name, raw, blocks)

    # ====== 阶段 9：清理临时目录 ======
    # try:
    #     shutil.rmtree(work, ignore_errors=True)
    #     print(f"[clean] 🧹 Removed work directory: {work}")
    # except Exception as e:
    #     print(f"[clean] ⚠️ Failed to remove work directory {work}: {e}")


# ========== 入口 ==========
if __name__=="__main__":
    load_dotenv()
    name=os.getenv("PROJECT_NAME")
    if not name: raise SystemExit("Please set PROJECT_NAME")
    concat_pipeline(name)
