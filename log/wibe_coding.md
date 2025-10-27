# Functional Request
## Request of refine the worker.py and pipeine.py

The pipeline.py as the main program, it will submit video generate request to silicon flow, 
invoke a new worker.py async function to start waiting the result.

Our text_video_silicon pipeline have worker.py, which is a back-ground thread that
poll the results from db/video_download.csv. 

It's a little bit chaos right now, these 2 jobs packed into 1 python thread. need to wait each other,
I want to split it into 2 thread. One is the main thread of pipeline, submit video, and if it's inQUeue or 
Submitted afterwards, then goes to the next block, if it return Wrong, or Too many request. It will retry.

Second thread is worker's background thread, it will chronos poll the result from db and log into ./log folder.

After the entire pipeline finished, it will set a timer to wait for the worker poll all video
downloaded. when all video's are done, then return.


## Combine the pipeline.py and concat.py

Write a new all together Python script, that support entire pipeline
First Use pipeline to generate video clip, when finish, use concat.py's ability
to concat everything together. User can Only use One click to generate the entire 
video.

do not need to re-write the concat and pipeline logic, re-use the logic already inside the pipeline.py and concat.py, 
just use their function as API, the cli is only the entry point


## Reconstruct the Project folder of Video

in worker.py and react_render/method.py, instead of store all the video and raw video in the project 
folder, flatten all together, I propose create a video folder and store all video into that folder.

## adapt both landscape video and 9:16 video

Currently the project only support 1280x720 format video,
help me add a new parameters in the json config file call size, use can choose both 
landscape and Tiktok format. You need to

1. add the option when generating Json file, support 2 format
2. modify the methods.react_render, let it support TikTok format record.
3. modify the correspond silicon flow generation format is `1280x720`,`720x1280`
4. modify the concat.py, let it support the TikTok format as well.

## remotion method

You've finished a wonderful exploration project, now make a subproject in this folder, follow my main project's API.
You need to write a sub model in my main project, to generate video clip.
```python
class BaseMethod(abc.ABC):
    NAME: str = "Base"        # Override
    OUTPUT_KIND: str = "any"  # "audio" | "video" | "other"

    def __init__(self) -> None:
        super().__init__()

    @abc.abstractmethod
    def run(self, *, prompt: str, project: str, target_name: str, text: str, workdir: Path, duration_ms: int | None = None, block) -> Dict[str, Any]:
        """Execute the method and return a dict:
        {{
          "ok": bool,
          "artifacts": [<paths>],
          "meta": {{...}},
          "error": <str or None>
        }}
        """
        raise NotImplementedError


    def generate_prompt(self, text: str) -> str:
        """Execute the method and return a str:
        prompt...
        """
        raise NotImplementedError
```

This is an exmple of using react to render a video, method.py, you need to create the own method.py for remotion block:
Right now the remotion only have 1 template, but later I may add more, so the specific template information is from block param.
If it's the correct template, render it, if not, raise Exception.
```python

@register_method
class ReactRenderMethod(BaseMethod):
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
```

After finished the method.py, add a new python file in the same folder called try_remotion.py, list some example
of using it, output into `./_test_out` folder.

## 

# test
## test pipeline
If I want to test the entire pipeine, help me mock every thing that need the API, 
that will cost lots of money, mock the API return, use @openai_demo2.json as the project json, 
create unit test file, and mock every needed function, test the pipeline's function, 
test the worker's function. 

create a folder for testing, in the future we may add lots of test file. 
then create a json file folder and put the json into that.
Abstract the mock api things into another python file, decouple the entire testing logic.