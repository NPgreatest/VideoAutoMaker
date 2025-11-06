#!/usr/bin/env python3
from __future__ import annotations
import os, json, re, subprocess
from pathlib import Path
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from dacite import from_dict
from dotenv import load_dotenv
from videogen.pipeline.schema import ScriptBlock
from videogen.pipeline.utils import read_json, write_json
from videogen.pipeline.add_picture import add_picture_overlay

# ========== 配置项 ==========
CRF = "14"             # 画质（越低越好）
PRESET = "slow"
AUDIO_RATE = "44100"
AUDIO_BR = "192k"
PIX_FMT = "yuv420p"

load_dotenv()
BGM_PATH = os.getenv("BGM_PATH")


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
    
    # Check in video/ subdirectory first, then project root
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
        ok = run([
            "ffmpeg","-y","-i",str(resized_video),"-i",str(audio),
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
    """Generate global subtitle file using block.text + clip duration."""
    blocks = [from_dict(ScriptBlock, b) for b in raw.get("script", [])]
    assert len(blocks) == len(clips), f"Script blocks ({len(blocks)}) != clips ({len(clips)})"

    total = 0.0
    idx = 1
    lines = []

    for block, clip in zip(blocks, clips):
        dur = get_duration(clip)
        start = total
        end = total + dur
        text = (block.text or "").strip()
        if text:
            lines.append(f"{idx}\n{fmt_time(start)} --> {fmt_time(end)}\n{text}\n\n")
            idx += 1
        total = end

    out_path.write_text("".join(lines), encoding="utf-8")
    print(f"[srt] ✅ generated precise subtitles -> {out_path}")


# ========== 阶段 5：拼接 ==========
def concat_videos(files: List[Path], out: Path)->bool:
    tmp = out.parent / "concat_list.txt"
    tmp.write_text("\n".join(f"file '{f.resolve()}'" for f in files),encoding="utf-8")
    ok = run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(tmp),
              "-c","copy","-movflags","+faststart",str(out)])
    if ok: print(f"[concat] ✅ {out}")
    return ok

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
    for i, block in enumerate(blocks, start=1):
        p=ensure_muxed(project_dir, i, muxed_dir, block)
        if p: clips.append(p)
    if not clips: raise SystemExit("❌ no muxed clips found")

    infos=[get_clip_info(p) for p in clips]
    w,h,fps=choose_target(infos, raw)
    print(f"[spec] Target {w}x{h}@{fps}fps")

    norm=[]
    for c in clips:
        out=norm_dir/f"{c.stem}_norm.mp4"
        if normalize_clip(c,out,w,h,fps): norm.append(out)
    if not norm: raise SystemExit("❌ normalize failed")

    final=work/"final.mp4"
    if not concat_videos(norm,final):
        raise SystemExit("concat failed")

    out_srt = work / "full.srt"
    generate_srt_from_json(raw, norm, out_srt)
    # Beautify and refine SRT -> project_name.srt
    try:
        from videogen.pipeline.beautify_srt import beautify_srt_at_path
        refined_srt = work / f"{project_name}.srt"
        beautify_srt_at_path(out_srt, refined_srt)
        print(f"[srt] ✅ refined -> {refined_srt}")
    except Exception as e:
        print(f"[srt] ⚠️ refine failed: {e}")
    print("✅ pipeline complete!")

    # ====== 阶段 6：添加图片叠加 ======
    final_with_picture = work / "final_with_picture.mp4"
    
    if not add_picture_overlay(final, final_with_picture):
        print("[picture] ⚠️ Failed to add picture overlay, using original video for subtitle burn-in.")
        final_with_picture = final  # 如果失败，使用原视频
    else:
        final = final_with_picture  # 更新 final 为带图片的视频，用于后续字幕烧录

    # ====== 阶段 7：字幕硬烧录（在图片层之上） ======
    burn_out = work / f"{project_name}_burn.mp4"
    font_path = Path("./assets/microhei.ttc").resolve()  # 你已有的字体路径，可替换

    # Prefer refined SRT if exists
    refined = work / f"{project_name}.srt"
    chosen_srt = refined if refined.exists() else out_srt

    if not chosen_srt.exists():
        print("[burn] ⚠️ No subtitle file found, skipping burn-in.")
    else:
        subtitles_filter = f"subtitles='{chosen_srt}':force_style='FontName={font_path.stem},FontSize=13," \
                           f"PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,BorderStyle=1," \
                           f"Outline=2,Shadow=0,MarginV=50,Alignment=8'"
        cmd = [
            "ffmpeg", "-y",
            "-i", str(final),  # 使用带图片的视频（如果有）
            "-vf", subtitles_filter,
            "-c:v", "libx264", "-preset", PRESET, "-crf", CRF,
            "-pix_fmt", PIX_FMT,
            "-c:a", "copy",
            str(burn_out)
        ]
        print(f"[burn] 🔥 Burning subtitles into video ...")
        ok = run(cmd)
        if ok:
            print(f"[burn] ✅ Subtitle burned video saved to: {burn_out}")
        else:
            print(f"[burn] ❌ Burn-in failed.")
            burn_out = final  # 如果烧录失败，使用之前的视频

    # ====== 阶段 8：添加背景音乐 ======
    # Determine input video: prefer burned subtitles, fallback to final
    input_video = burn_out if burn_out.exists() else final
    
    bgm_path = Path(BGM_PATH)
    
    if not bgm_path.exists():
        print(f"[bgm] ⚠️ BGM file not found: {bgm_path}, skipping BGM addition.")
    else:
        final_with_bgm = work / f"{project_name}_final.mp4"
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


# ========== 入口 ==========
if __name__=="__main__":
    load_dotenv()
    name=os.getenv("PROJECT_NAME")
    if not name: raise SystemExit("Please set PROJECT_NAME")
    concat_pipeline(name)
