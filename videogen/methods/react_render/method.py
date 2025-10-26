from __future__ import annotations
import http.server, socketserver, threading
import json, subprocess, tempfile, re, html, shutil
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Any

from videogen.methods.base import BaseMethod
from videogen.methods.registry import register_method
from videogen.llm_engine import get_engine, LLMConfigError

try:
    from playwright.sync_api import sync_playwright
    _PLAYWRIGHT_OK = True
except Exception:
    _PLAYWRIGHT_OK = False


HERE = Path(__file__).resolve().parent
TEMPLATE_HTML = HERE / "html_template.html"

REACT_UMD = "https://unpkg.com/react@18/umd/react.production.min.js"
REACTDOM_UMD = "https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"
BABEL_UMD = "https://unpkg.com/@babel/standalone/babel.min.js"

MAX_LLM_RETRIES = 3


def _which(cmd: str) -> bool:
    return shutil.which(cmd) is not None

def validate_html(engine: Any, html_text: str) -> bool:
    """
    Ask LLM to validate if HTML is runnable for React video generation.
    Returns True if it seems valid (single <html>, <script type="text/babel">, etc.)
    """
    validate_prompt = (
        "You are a strict validator. "
        "I will give you a full HTML page that should display a short React 18 UMD + Babel animation. "
        "If it looks valid enough to render (no syntax errors, no nested <html>, "
        "includes at least one <script type='text/babel'> with ReactDOM.render or createRoot), "
        "respond strictly with 'True'. "
        "If it seems broken, missing scripts, or malformed, respond strictly with 'False'. "
        "Output only 'True' or 'False'."
    )

    try:
        ans = engine.ask_text(f"{validate_prompt}\n\nHTML:\n{html_text[:6000]}")
        ans = ans.strip().lower()
        return "true" in ans and "false" not in ans
    except Exception as e:
        print(f"[Validator] Validation error: {e}")
        return False

def get_video_duration(video_path: Path) -> float:
    """用 ffprobe 精确获取视频时长（秒）"""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json", str(video_path)
        ],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])


def _build_index_html(title: str, width: int, height: int, html_code: str, duration_sec: float) -> str:
    """注入模板生成完整 HTML"""
    template = TEMPLATE_HTML.read_text(encoding="utf-8")
    return (
        template
        .replace("{{TITLE}}", html.escape(title))
        .replace("{{WIDTH}}", str(width))
        .replace("{{HEIGHT}}", str(height))
        .replace("{{REACT_UMD}}", REACT_UMD)
        .replace("{{REACTDOM_UMD}}", REACTDOM_UMD)
        .replace("{{BABEL_UMD}}", BABEL_UMD)
        .replace("{{DURATION_MS}}", str(int(duration_sec) * 1000))
        .replace("{{HTML_CONTENT}}", html_code)
    )


def _sanitize_html(raw: str) -> str:
    """Clean fences, wrappers, and duplicates."""
    text = (raw or "").strip()
    text = re.sub(r"^```[\s\S]*?\n", "", text)
    text = re.sub(r"\n```$", "", text)
    text = re.sub(r'<div\s+id=["\']root["\']><\/div>', '', text, flags=re.I)
    text = text.replace("```html", "").replace("```", "")
    text = text.strip()

    body_match = re.search(r"<body[^>]*>([\s\S]*?)</body>", text, re.I)
    if body_match:
        text = body_match.group(1).strip()

    text = re.sub(r"<!DOCTYPE[^>]*>", "", text, flags=re.I)
    text = re.sub(r"<\/?(html|head)>", "", text, flags=re.I)
    text = re.sub(r"(?:Here'?s|This implementation features|The animation sequence)[\s\S]+", "", text, flags=re.I)
    return text.strip()


@contextmanager
def _serve_dir(root_dir: Path):
    Handler = lambda *args, **kw: http.server.SimpleHTTPRequestHandler(*args, directory=str(root_dir), **kw)
    with socketserver.ThreadingTCPServer(("127.0.0.1", 0), Handler) as httpd:
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        try:
            yield httpd.server_address[1]
        finally:
            httpd.shutdown(); httpd.server_close(); t.join()

def _record_url(
    page_url: str,
    out_video: Path,
    width: int,
    height: int,
    duration_ms: int,
    fps: int = 60,
    extra_record_ms: int = 1000,
) -> Path:
    """
    精确帧控制：输出 mp4 时长严格等于 duration_ms（误差 < 1帧）。
    """
    out_video.parent.mkdir(parents=True, exist_ok=True)
    tmp_webm = out_video.with_suffix(".webm")

    # === Step 1. 录制 ===
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": width, "height": height},
            record_video_dir=str(out_video.parent),
            record_video_size={"width": width, "height": height},
            device_scale_factor=3,
        )
        page = context.new_page()
        page.goto(page_url, wait_until="networkidle")

        total_wait_ms = duration_ms + extra_record_ms
        try:
            page.wait_for_function("() => window.__PLAY_DONE === true", timeout=total_wait_ms + 4000)
        except Exception:
            page.wait_for_timeout(total_wait_ms)

        tmp_path = Path(page.video.path())
        context.close()
        browser.close()

    tmp_path.replace(tmp_webm)

    # === Step 2. 帧数精确转码 ===
    target_sec = duration_ms / 1000.0
    frame_count = int(round(target_sec * fps))
    tmp_fixed = out_video.with_suffix(".mp4")

    cmd = [
        "ffmpeg", "-y",
        "-i", str(tmp_webm),
        "-vf", f"scale={width}:{height}:flags=lanczos,fps={fps}",
        "-frames:v", str(frame_count),       # ✅ 输出精确帧数
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "14",
        "-pix_fmt", "yuv420p",
        "-an",                                # 无音轨避免时间线漂移
        str(tmp_fixed),
    ]
    subprocess.run(cmd, check=True)

    tmp_webm.unlink(missing_ok=True)

    real_duration = get_video_duration(tmp_fixed)
    print(f"[OK] 输出文件长度: {real_duration:.3f}s  (目标 {target_sec:.3f}s, 帧数 {frame_count})")
    return tmp_fixed


@register_method
class ReactRenderMethod(BaseMethod):
    """
    Prompt → HTML+React → index.html + 录制视频
    Adds: LLM validation + retry
    """
    NAME = "react_animation"
    OUTPUT_KIND = "video"

    DEFAULT_W = 1920
    DEFAULT_H = 1080
    DEFAULT_SEC = 10.0
    
    # Video format configurations
    FORMATS = {
        "landscape": {"width": 1280, "height": 720},
        "tiktok": {"width": 720, "height": 1280}
    }

    def run(
        self,
        *,
        prompt: str,
        project: str,
        target_name: str,
        text: str,
        workdir: Path,
        duration_ms: int | None = None,
        block: Any | None = None,
    ) -> Dict[str, Any]:
        if not text.strip():
            return {"ok": False, "error": "text 不能为空"}

        out_dir = workdir / "project" / project
        out_dir.mkdir(parents=True, exist_ok=True)
        video_dir = out_dir / "video"
        video_dir.mkdir(parents=True, exist_ok=True)
        out_html = out_dir / f"{target_name}.html"
        out_video = video_dir / f"{target_name}.mp4"

        # Read project configuration to determine video format
        project_config_path = workdir / "project" / project / f"{project}.json"
        video_format = "landscape"  # default
        
        if project_config_path.exists():
            try:
                import json
                with open(project_config_path, 'r', encoding='utf-8') as f:
                    project_config = json.load(f)
                    video_format = project_config.get("size", "landscape")
            except Exception as e:
                print(f"[ReactRender] Warning: Could not read project config: {e}")
        
        # Get dimensions based on format
        if video_format in self.FORMATS:
            format_config = self.FORMATS[video_format]
            width = format_config["width"]
            height = format_config["height"]
        else:
            # Fallback to default
            width = self.DEFAULT_W
            height = self.DEFAULT_H
            
        duration_sec = (duration_ms / 1000.0) if duration_ms else self.DEFAULT_SEC
        duration_ms_final = int(duration_sec * 1000)

        try:
            engine = get_engine()
        except LLMConfigError as e:
            return {"ok": False, "error": f"LLM 配置错误: {e}"}

        sys_prompt = (
            "You are a professional motion designer using React 18 UMD + Babel. "
            "Generate an HTML fragment (not a full <html> page). "
            "Do NOT include <html>, <head>, <body>, or extra <div id='root'> elements. "
            "Your code will be injected inside an existing <div id='root'>. "
            "Use React JSX (within <script type='text/babel'>) and optional <style>. "
            "Center all visual elements with CSS Grid or Flexbox. "
            "Use a clean, minimal, modern design (white, gray, light blue). "
            "Keep animations declarative and smooth. "
            "Output only the HTML fragment — no explanations."
        )

        last_err = None
        html_clean = None
        full_html = None

        # === generation + validation loop ===
        for attempt in range(1, MAX_LLM_RETRIES + 1):
            try:
                print(f"[LLM] Generating attempt {attempt}/{MAX_LLM_RETRIES} ...")
                raw_html = engine.ask_text(f"{sys_prompt}\n\nPrompt: {text}")
                html_clean = _sanitize_html(raw_html)
                full_html = _build_index_html(
                    title=f"{project}:{target_name}",
                    width=width, height=height,
                    html_code=html_clean,
                    duration_sec=duration_sec,
                )

                print("[LLM] Validating HTML...")
                if validate_html(engine, full_html):
                    print("[LLM] ✅ HTML validated as runnable.")
                    break
                else:
                    print("[LLM] ❌ Invalid HTML, retrying...")
                    last_err = "Validation failed"
                    continue
            except Exception as e:
                last_err = str(e)
                print(f"[LLM] Error during generation attempt {attempt}: {e}")
                continue
        else:
            return {"ok": False, "error": f"LLM failed to generate valid HTML after {MAX_LLM_RETRIES} attempts: {last_err}"}

        out_html.write_text(full_html, encoding="utf-8")

        try:
            with tempfile.TemporaryDirectory(prefix="react_html_") as td:
                tmp_dir = Path(td)
                tmp_index = tmp_dir / "index.html"
                tmp_index.write_text(full_html, encoding="utf-8")
                with _serve_dir(tmp_dir) as port:
                    url = f"http://127.0.0.1:{port}/index.html"
                    final_path = _record_url(url, out_video, width, height, duration_ms_final)
        except subprocess.CalledProcessError as e:
            return {"ok": False, "artifacts": [str(out_html)], "error": f"ffmpeg 失败: {e}"}
        except Exception as e:
            return {"ok": False, "artifacts": [str(out_html)], "error": str(e)}

        return {
            "ok": True,
            "artifacts": [str(out_html), str(final_path)],
            "meta": {
                "mode": "html-validated",
                "width": width,
                "height": height,
                "durationSec": duration_sec,
                "html": str(out_html),
                "output_path": str(final_path),
                "attempts": attempt,
            },
            "error": None,
        }

    def generate_prompt(self, text: str) -> str:
        engine = get_engine()

        system_prompt = (
            "You are a professional motion designer creating educational or explanatory scenes in React.\n"
            "You visualize structured or numerical information (counts, lists, flight paths, timelines, etc.).\n"
            "Your goal is to describe a clean, elegant, data-driven animation scene.\n"
            "The result will later be converted into React code, so focus on clear visual layout and composition.\n"
            "Avoid cinematic storytelling or people; instead, focus on charts, maps, or UI-like animations.\n"
        )
        user_prompt = (
            f"Line: {text}\n\n"
            "Describe what kind of React animation should visualize this information. "
            "Mention elements (icons, text labels, bars, flight paths, charts) and how they animate. "
            "Avoid writing code, only describe the intended look and movement."
        )

        res = engine.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
            max_tokens=300,
        )
        return res["content"].strip()