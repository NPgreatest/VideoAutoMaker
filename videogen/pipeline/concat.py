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

# ========== 配置项 ==========
CRF = "14"             # 画质（越低越好）
PRESET = "slow"
AUDIO_RATE = "44100"
AUDIO_BR = "192k"
PIX_FMT = "yuv420p"

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
def ensure_muxed(project_dir: Path, idx: int) -> Optional[Path]:
    mux = project_dir / f"L{idx}_muxed.mp4"
    if mux.exists(): return mux
    
    # Check in video/ subdirectory first, then project root
    video = project_dir / "video" / f"L{idx}.mp4"
    if not video.exists():
        video = project_dir / f"L{idx}.mp4"
    
    audio = project_dir / f"audio/L{idx}.wav"
    
    if video.exists() and audio.exists():
        print(f"[mux] Generating L{idx}_muxed.mp4 ...")
        ok = run([
            "ffmpeg","-y","-i",str(video),"-i",str(audio),
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

    clips=[]
    for i,_ in enumerate(raw["script"],start=1):
        p=ensure_muxed(project_dir,i)
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
    print("✅ pipeline complete!")

    # ====== 阶段 6：字幕硬烧录 ======
    burn_out = work / f"{project_name}_burn.mp4"
    font_path = Path("./assets/microhei.ttc").resolve()  # 你已有的字体路径，可替换

    if not out_srt.exists():
        print("[burn] ⚠️ No subtitle file found, skipping burn-in.")
    else:
        subtitles_filter = f"subtitles='{out_srt}':force_style='FontName={font_path.stem},FontSize=22," \
                           f"PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,BorderStyle=1," \
                           f"Outline=2,Shadow=0,MarginV=50,Alignment=2'"
        cmd = [
            "ffmpeg", "-y",
            "-i", str(final),
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


# ========== 入口 ==========
if __name__=="__main__":
    load_dotenv()
    name=os.getenv("PROJECT_NAME")
    if not name: raise SystemExit("Please set PROJECT_NAME")
    concat_pipeline(name)
