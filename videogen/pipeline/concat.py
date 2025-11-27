#!/usr/bin/env python3
from __future__ import annotations
import os, json, subprocess, shutil
from pathlib import Path
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from dacite import from_dict
from dotenv import load_dotenv
from videogen.pipeline.utils import read_json
from videogen.pipeline.gen_cover import gen_cover
from videogen.schema.project_schema import ScriptBlock
from videogen.dao.working_block_dao import WorkingBlockDAO
from videogen.pipeline.working_block import WorkingBlockStatus

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
    proc = subprocess.run(cmd, capture_output=True)
    stderr = proc.stderr.decode("utf-8", errors="ignore")
    stdout = proc.stdout.decode("utf-8", errors="ignore")
    if proc.returncode != 0:
        print(proc.stderr[-400:])
        return False
    return True

def ffprobe(path: Path) -> Dict:
    cmd = ["ffprobe","-v","error","-show_streams","-show_format","-print_format","json",str(path)]
    out = subprocess.check_output(cmd, encoding="utf-8")
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

# ========== 阶段 1：从 WorkingBlockDAO 获取 block 的最后一个节点 ==========
def get_last_node_in_chain(dao: WorkingBlockDAO, project_name: str, block_id: str) -> Optional[str]:
    """
    Find the last node (leaf node) in the chain for a given block_id.
    The last node is the one that has no other nodes depending on it (not in any prev_ids).
    """
    # Get all working blocks for this project and block_id
    all_blocks = dao.get_all(project_name)
    block_blocks = [wb for wb in all_blocks if wb.block_id == block_id and wb.status == WorkingBlockStatus.SUCCESS]
    
    if not block_blocks:
        return None

    block_blocks.sort(key=lambda wb: wb.action_index)
    return block_blocks[-1].id

def get_audio_block_for_block_id(dao: WorkingBlockDAO, project_name: str, block_id: str) -> Optional[str]:
    """Find the fish_audio working block for a given block_id.
    Uses action_index to find the first fish_audio action (typically action_index=0).
    """
    # Try to get by method_name first (optimized query)
    audio_block = dao.get_by_method_name(project_name, block_id, "fish_audio")
    if audio_block and audio_block.status == WorkingBlockStatus.SUCCESS:
        return audio_block.id
    
    # Fallback: search all blocks (for backward compatibility)
    all_blocks = dao.get_all(project_name)
    audio_blocks = [
        wb for wb in all_blocks 
        if wb.block_id == block_id 
        and wb.method_name == "fish_audio" 
        and wb.status == WorkingBlockStatus.SUCCESS
    ]
    
    if not audio_blocks:
        return None
    
    # Return the one with the lowest action_index (first action)
    audio_blocks.sort(key=lambda wb: wb.action_index if wb.action_index is not None else 999)
    return audio_blocks[0].id

def ensure_muxed(project_dir: Path, block_id: str, muxed_dir: Path, dao: WorkingBlockDAO, project_name: str) -> Optional[Path]:
    """
    Generate muxed video from the last node in chain for a block_id.
    Uses WorkingBlockDAO to find the last node and audio source.
    """
    # Check and generate in muxed_dir
    mux = muxed_dir / f"{block_id}_muxed.mp4"
    if mux.exists(): 
        return mux
    
    # Get the last node in chain for this block
    last_node_id = get_last_node_in_chain(dao, project_name, block_id)
    if not last_node_id:
        print(f"[mux] ⚠️ No last node found for block {block_id}, skipping")
        return None
    
    last_node = dao.get_working_block(last_node_id)
    if not last_node or not last_node.output_path:
        print(f"[mux] ⚠️ Last node {last_node_id} has no output_path, skipping")
        return None
    
    video_path = Path(last_node.output_path)
    if not video_path.exists():
        print(f"[mux] ⚠️ Video file not found: {video_path}, skipping")
        return None
    
    # Get audio block for this block_id
    audio_node_id = get_audio_block_for_block_id(dao, project_name, block_id)
    if not audio_node_id:
        print(f"[mux] ⚠️ No audio block found for block {block_id}, skipping")
        return None
    
    audio_node = dao.get_working_block(audio_node_id)
    if not audio_node or not audio_node.output_path:
        print(f"[mux] ⚠️ Audio node {audio_node_id} has no output_path, skipping")
        return None
    
    audio_path = Path(audio_node.output_path)
    if not audio_path.exists():
        print(f"[mux] ⚠️ Audio file not found: {audio_path}, skipping")
        return None
    
    # Get audio duration to determine if we need to loop video
    audio_info = ffprobe(audio_path)
    audio_dur = float(audio_info.get("format", {}).get("duration", 0))
    
    # Get video duration
    video_info = ffprobe(video_path)
    video_dur = float(video_info.get("format", {}).get("duration", 0))
    
    print(f"[mux] Generating {block_id}_muxed.mp4 from last node {last_node_id}...")
    print(f"[mux] Video: {video_path}")
    print(f"[mux] Audio: {audio_path}")
    print(f"[mux] Video duration: {video_dur:.2f}s, Audio duration: {audio_dur:.2f}s")
    
    # If video is shorter than audio, loop it until it reaches audio duration
    if video_dur < audio_dur and video_dur > 0:
        print(f"[mux] Video is shorter than audio, looping video to match audio duration...")
        # Use stream_loop to loop the video input, then trim to audio duration
        ok = run([
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", str(video_path),  # Loop input video infinitely
            "-i", str(audio_path),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "libx264", "-preset", PRESET, "-crf", CRF,
            "-c:a", "aac", "-ar", AUDIO_RATE, "-b:a", AUDIO_BR,
            "-pix_fmt", PIX_FMT,
            "-shortest",  # Use shortest to match audio duration (stops when audio ends)
            str(mux)
        ])
    else:
        # Video is longer or equal to audio, use shortest to match audio
        ok = run([
            "ffmpeg", "-y", "-i", str(video_path), "-i", str(audio_path),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-ar", AUDIO_RATE, "-b:a", AUDIO_BR,
            "-shortest", str(mux)
        ])
    
    return mux if ok else None

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

def generate_srt_from_blocks(dao: WorkingBlockDAO, project_name: str, block_ids: List[str], clips: List[Path], out_path: Path) -> None:
    """
    Generate SRT file from WorkingBlockDAO data.
    优先使用 audio block 的 result_json 里的 segments，
    否则 fallback 到 block text + clip 时长。
    每个 segment 都会单独显示，时间戳会加上前面所有 clips 的累计时长。
    """
    idx = 1
    lines = []
    block_index = 0  # Track current block index for calculating offset

    for block_id, clip in zip(block_ids, clips):
        # 计算当前 block 在整个视频中的起始时间（前面所有 clips 的累计时长）
        block_offset = sum(float(get_duration(c)) for c in clips[:block_index])
        
        # 获取该 block 的 audio block
        audio_node_id = get_audio_block_for_block_id(dao, project_name, block_id)
        segments = None
        block_text = None
        
        if audio_node_id:
            audio_node = dao.get_working_block(audio_node_id)
            if audio_node and audio_node.result_json:
                try:
                    result_data = json.loads(audio_node.result_json)
                    # Try to get segments from result_json
                    if isinstance(result_data, dict):
                        segments = result_data.get("segments")
                except (json.JSONDecodeError, TypeError):
                    pass
        
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

        # fallback: 使用整个 clip 时长，尝试从 config_json 获取 text
        dur = get_duration(clip)
        text = ""
        
        # Try to get text from any working block's config_json for this block_id
        all_blocks = dao.get_all(project_name)
        for wb in all_blocks:
            if wb.block_id == block_id:
                try:
                    config = json.loads(wb.config_json or "{}")
                    if "text" in config:
                        text = config["text"].strip()
                        break
                except (json.JSONDecodeError, TypeError):
                    pass
        
        if text:
            start = block_offset
            end = start + dur
            lines.append(f"{idx}\n{fmt_time(start)} --> {fmt_time(end)}\n__SEG__:{text}\n\n")
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
    work=project_dir/"_work"; work.mkdir(exist_ok=True)
    muxed_dir=work/"muxed"; muxed_dir.mkdir(exist_ok=True)
    norm_dir=work/"norm"; norm_dir.mkdir(exist_ok=True)

    # Get working blocks from DAO
    dao = WorkingBlockDAO()
    all_blocks = dao.get_all(project_name)
    
    # Group by block_id and get unique block_ids
    block_ids_set = {wb.block_id for wb in all_blocks if wb.block_id}
    # Sort block_ids (e.g., L1, L2, L3...)
    block_ids = sorted(block_ids_set, key=lambda x: (x[0], int(x[1:]) if len(x) > 1 and x[1:].isdigit() else 0))
    
    if not block_ids:
        raise SystemExit("❌ no blocks found in database")
    
    print(f"[concat] Found {len(block_ids)} blocks: {block_ids}")
    
    clips=[]
    clip_block_ids=[]
    for block_id in block_ids:
        p=ensure_muxed(project_dir, block_id, muxed_dir, dao, project_name)
        if p:
            clips.append(p)
            clip_block_ids.append(block_id)
    if not clips: raise SystemExit("❌ no muxed clips found")

    # Try to get project config for choose_target
    project_config = None
    project_json_path = project_dir / f"{project_name}.json"
    if project_json_path.exists():
        try:
            project_config = read_json(project_json_path)
        except Exception:
            pass

    infos=[get_clip_info(p) for p in clips]
    w,h,fps=choose_target(infos, project_config)
    print(f"[spec] Target {w}x{h}@{fps}fps")

    norm = []
    for c in clips:
        out = norm_dir / f"{c.stem}_norm.mp4"
        if out.exists():
            print(f"[norm] 🟡 Skip (cached): {out}")
            norm.append(out)
            continue

        print(f"[norm] 🔵 Normalizing: {c} -> {out}")
        if normalize_clip(c, out, w, h, fps):
            norm.append(out)

    final=work/"final.mp4"
    if not concat_videos(norm,final):
        raise SystemExit("concat failed")

    # Generate and beautify SRT directly -> project_name.srt
    out_srt = work / f"{project_name}.srt"
    # First generate raw SRT to a temp file
    temp_srt = work / "temp_srt.srt"
    generate_srt_from_blocks(dao, project_name, clip_block_ids, norm, temp_srt)
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

    # Check if subtitle burning is enabled
    burn_subtitle = True
    project_json_path = project_dir / f"{project_name}.json"
    if project_json_path.exists():
        try:
            raw = read_json(project_json_path)
            burn_subtitle = raw.get("burn_subtitle", True)
        except Exception:
            pass

    if not burn_subtitle:
        print("[burn] ⏭️ Subtitle burning is disabled, skipping.")
        shutil.copy2(final, burn_out)
    else:
        # Pick SRT file
        refined = work / f"{project_name}.srt"
        chosen_srt = refined if refined.exists() else out_srt

        if not chosen_srt.exists():
            print("[burn] ⚠️ No subtitle file found, skipping burn-in.")
            shutil.copy2(final, burn_out)
        else:
            #
            # ---------------------------------------------------------
            # 🚨 核心补丁：创建 ASCII-only 临时目录执行 FFmpeg
            # ---------------------------------------------------------
            #
            tmp_dir = Path("C:/temp/ffmpeg_run")
            tmp_dir.mkdir(parents=True, exist_ok=True)

            # Copy input video to safe ASCII path
            tmp_input = tmp_dir / "input.mp4"
            shutil.copy2(final, tmp_input)

            # Copy subtitle file to safe ASCII path
            safe_srt = tmp_dir / "subtitle.srt"
            shutil.copy2(chosen_srt, safe_srt)

            # Output path in safe ASCII dir
            tmp_output = tmp_dir / "output_nobgm.mp4"

            # Convert paths to ffmpeg-safe format
            font_name = Path(FONT_PATH).stem if FONT_PATH else "Arial"

            # ----------------------------------------------
            # Windows FFmpeg 4.2 字幕路径兼容处理
            # ----------------------------------------------

            # WRONG (你现在代码里是这个)
            # srt_path = str(temp_srt.resolve())

            # CORRECT（必须替换成 safe_srt）
            srt_path = str(safe_srt.resolve())
            srt_path = srt_path.replace("\\", "/")

            # FFmpeg 4.2 路径补丁
            if ":/" in srt_path:
                drive, rest = srt_path.split(":/", 1)
                srt_path = f"{drive}\\:/{rest}"

            font_name = Path(FONT_PATH).stem if FONT_PATH else "Arial"

            # 黄色 PrimaryColour=&H00FFFF00
            subtitles_filter = (
                f"subtitles=filename='{srt_path}':"
                f"force_style='FontName={font_name},"
                f"FontSize=20,PrimaryColour=&H00FFFF00,"
                f"OutlineColour=&H00000000,BorderStyle=1,"
                f"Outline=2,Shadow=0,Alignment=2,"
                f"MarginL=40,MarginR=40,MarginV=60'"
            )

            cmd = [
                "ffmpeg", "-y",
                "-i", str(tmp_input),
                "-vf", subtitles_filter,
                "-c:v", "libx264", "-preset", PRESET, "-crf", CRF,
                "-pix_fmt", PIX_FMT,
                "-c:a", "copy",
                str(tmp_output)
            ]

            print("[burn] 🔥 Burning subtitles inside ASCII-only temp dir ...")
            ok = run(cmd)

            if ok and tmp_output.exists():
                # Copy the safe output back to the desired path
                shutil.copy2(tmp_output, burn_out)
                print(f"[burn] ✅ Subtitle burned video saved to: {burn_out}")
            else:
                print("[burn] ❌ Burn-in failed, copying original instead.")
                shutil.copy2(final, burn_out)

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
    bgm_path_str = None
    if project_json_path.exists():
        try:
            raw = read_json(project_json_path)
            bgm_path_str = raw.get("bgm_path")
        except Exception:
            pass
    
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
    # Try to get project JSON for gen_cover
    raw = {}
    blocks = []
    if project_json_path.exists():
        try:
            raw = read_json(project_json_path)
            blocks = [from_dict(ScriptBlock, b) for b in raw.get("script", [])]
        except Exception:
            pass
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
