#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from wiki2video.config.config_manager import config
from wiki2video.config.config_vars import ENSURE_OUTPUT
from wiki2video.core.paths import get_project_dir, get_project_json_path
from wiki2video.core.utils import read_json
from wiki2video.core.working_block import WorkingBlockStatus
from wiki2video.dao.working_block_dao import WorkingBlockDAO

# ========== 配置 ==========
CRF = "14"
PRESET = "slow"
AUDIO_RATE = "44100"
AUDIO_BR = "192k"
PIX_FMT = "yuv420p"

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = PACKAGE_ROOT / "assets" / "placeholder"
PLACEHOLDER_VIDEO = ASSETS_DIR / "placeholder.mp4"
PLACEHOLDER_AUDIO = ASSETS_DIR / "placeholder.mp3"


# ========== ffmpeg helpers ==========
def run(cmd: List[str]) -> bool:
    print("[ffmpeg]", " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0:
        print(proc.stderr.decode("utf-8", errors="ignore")[-400:])
        return False
    return True


def ffprobe(path: Path) -> Dict:
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-print_format", "json", str(path)],
        encoding="utf-8",
    )
    return json.loads(out)


def parse_fps(s: str) -> float:
    if not s or s == "0/0":
        return 30
    n, d = map(float, s.split("/")) if "/" in s else (float(s), 1)
    return n / d


@dataclass
class ClipInfo:
    path: Path
    w: int
    h: int
    fps: float
    has_audio: bool


def get_clip_info(p: Path) -> ClipInfo:
    d = ffprobe(p)
    v = next(s for s in d["streams"] if s["codec_type"] == "video")
    a = [s for s in d["streams"] if s["codec_type"] == "audio"]
    return ClipInfo(
        p,
        int(v["width"]),
        int(v["height"]),
        parse_fps(v.get("r_frame_rate") or v.get("avg_frame_rate")),
        bool(a),
    )


# ========== DAO helpers ==========
def get_last_node_in_chain(dao: WorkingBlockDAO, project_id: str, block_id: str) -> Optional[str]:
    blocks = [
        wb
        for wb in dao.get_all(project_id)
        if wb.block_id == block_id and wb.status == WorkingBlockStatus.SUCCESS
    ]
    if not blocks:
        return None
    blocks.sort(key=lambda wb: wb.action_index)
    return blocks[-1].id


def get_audio_block_for_block_id(dao: WorkingBlockDAO, project_id: str, block_id: str) -> Optional[str]:
    audio = [
        wb
        for wb in dao.get_by_block(project_id, block_id)
        if wb.method_name == "text_audio" and wb.status == WorkingBlockStatus.SUCCESS
    ]
    if not audio:
        return None
    audio.sort(key=lambda wb: wb.action_index or 999)
    return audio[0].id


def ensure_muxed(
    project_dir: Path,
    block_id: str,
    muxed_dir: Path,
    dao: WorkingBlockDAO,
    project_id: str,
) -> Optional[Path]:
    mux = muxed_dir / f"{block_id}_muxed.mp4"
    if mux.exists():
        return mux

    last_id = get_last_node_in_chain(dao, project_id, block_id)
    audio_id = get_audio_block_for_block_id(dao, project_id, block_id)

    video = None
    audio = None

    if last_id:
        wb = dao.get_by_id(last_id)
        if wb and wb.output_path:
            p = Path(wb.output_path)
            if p.exists():
                video = p

    if audio_id:
        wb = dao.get_by_id(audio_id)
        if wb and wb.output_path:
            p = Path(wb.output_path)
            if p.exists():
                audio = p

    # ====== ENSURE_OUTPUT 兜底 ======
    if ENSURE_OUTPUT:
        if not video:
            print(f"[ensure] ⚠️ block {block_id} missing video, using placeholder")
            video = PLACEHOLDER_VIDEO
        if not audio:
            print(f"[ensure] ⚠️ block {block_id} missing audio, using placeholder")
            audio = PLACEHOLDER_AUDIO
    else:
        if not video or not audio:
            return None

    # ====== mux ======
    try:
        vd = float(ffprobe(video)["format"]["duration"])
        ad = float(ffprobe(audio)["format"]["duration"])
    except Exception:
        if ENSURE_OUTPUT:
            shutil.copy2(PLACEHOLDER_VIDEO, mux)
            return mux
        return None

    if vd < ad:
        ok = run([
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", str(video),
            "-i", str(audio),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "libx264", "-preset", PRESET, "-crf", CRF,
            "-c:a", "aac", "-ar", AUDIO_RATE, "-b:a", AUDIO_BR,
            "-pix_fmt", PIX_FMT,
            "-shortest",
            str(mux),
        ])
    else:
        ok = run([
            "ffmpeg", "-y",
            "-i", str(video),
            "-i", str(audio),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac", "-ar", AUDIO_RATE, "-b:a", AUDIO_BR,
            "-shortest",
            str(mux),
        ])

    if not ok and ENSURE_OUTPUT:
        print(f"[ensure] ❌ mux failed, fallback placeholder for {block_id}")
        shutil.copy2(PLACEHOLDER_VIDEO, mux)

    return mux if mux.exists() else None


# ========== normalize / concat ==========
def choose_target(infos: List[ClipInfo], cfg: Dict | None) -> Tuple[int, int, int]:
    if cfg and cfg.get("size") == "tiktok":
        return 720, 1280, 30
    if cfg and cfg.get("size") == "landscape":
        return 1280, 720, 30
    fps = Counter(round(i.fps) for i in infos).most_common(1)[0][0]
    return max(i.w for i in infos), max(i.h for i in infos), fps


def normalize_clip(src: Path, dst: Path, w: int, h: int, fps: int) -> bool:
    vf = f"scale={w}:{h}:force_original_aspect_ratio=decrease," \
         f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,fps={fps},format={PIX_FMT}"
    return run([
        "ffmpeg", "-y",
        "-i", str(src),
        "-vf", vf,
        "-c:v", "libx264", "-preset", PRESET, "-crf", CRF,
        "-c:a", "aac", "-ar", AUDIO_RATE, "-b:a", AUDIO_BR,
        str(dst),
    ])


def concat_videos(files: List[Path], out: Path) -> bool:
    lst = out.parent / "concat.txt"
    lst.write_text(
        "\n".join(f"file '{f.as_posix()}'" for f in files),
        encoding="utf-8",
    )
    return run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(lst),
        "-c", "copy",
        "-movflags", "+faststart",
        str(out),
    ])


# ========== 主 pipeline ==========
def concat_pipeline(project_id: str):
    project_dir = get_project_dir(project_id)
    work = project_dir / "_work"
    work.mkdir(exist_ok=True)

    dao = WorkingBlockDAO()
    block_ids = sorted({wb.block_id for wb in dao.get_all(project_id) if wb.block_id})

    muxed = []
    for bid in block_ids:
        p = ensure_muxed(project_dir, bid, work, dao, project_id)
        if p:
            muxed.append(p)

    if not muxed and ENSURE_OUTPUT:
        print("[ensure] ⚠️ no valid blocks, using single placeholder video")
        muxed = [PLACEHOLDER_VIDEO]

    infos = [get_clip_info(p) for p in muxed]
    cfg = read_json(get_project_json_path(project_id)) if get_project_json_path(project_id).exists() else {}
    w, h, fps = choose_target(infos, cfg)

    norm = []
    for c in muxed:
        o = work / f"{c.stem}_norm.mp4"
        normalize_clip(c, o, w, h, fps)
        norm.append(o)

    final = work / "final.mp4"
    concat_videos(norm, final)

    out = project_dir / f"{project_id}.mp4"
    shutil.copy2(final, out)

    print(f"✅ Final video written to {out}")



    # SRT + cover
    # from wiki2video.core.beautify_srt import beautify_srt_at_path
    # srt = project_dir / f"{project_id}.srt"
    # generate_srt_from_blocks(dao, project_id, block_ids, norm, srt)
    # beautify_srt_at_path(srt, srt)

    # raw = read_json(get_project_json_path(project_id)) if get_project_json_path(project_id).exists() else {}
    # blocks = [from_dict(ScriptBlock, b) for b in raw.get("script", [])]
    # gen_cover(project_dir, project_id, raw, blocks)

    print("✅ pipeline complete")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("project_id")
    concat_pipeline(p.parse_args().project_id)
