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

## Refactor the project based on the new schema
I refactor the schema.py, update some fields, the WorkingBlock will store in SQLite, instead of 
using db/video_download.csv, create a SQLite file, and store the working block in it.
So you need to refactor the worker.py. abstract the worker into a global feature, the remotion and text_video_silicon
will use the same Global worker, method->run function only create the WorkingBlock and push into the SQLite. at the end 
of the pipeline, start the worker and keep waiting for the result.

## Add the feature of integrate image file to single block
The new method remotion need integrate image file into that single block, picture will stay in the project
folder, and will named {id}.jpg, the ScriptBlock `extra_info` will contains `single_picture` field and the value is the 
image file name. `remotion_animation/method.py` will read the image file and inject into the `remotion_animation/remotion_project/public/assets` 
folder, and the method.py will inject that image file into the video, delete the image file inside `public/assets` the video is rendered.


## Add the feature of entire runnable pipeline
Finish the generate.py in /videogen/cli, the entire pipeline include:
1. call the pipeline, try to generate all resources
2. Validate the result, if everything is passed, then goto concat step
2.1. if some job failed, re-run the pipeline again, each block have a retry times,
if it exceed the max_retry(add it in the .env file), then return error and stop the entire pipeline, mark
the pipeline is failed in the json file, later if another program call pipeline it will just skip and return.
3. Concat the video, if everything is passed, then goto the end

You need to polish the validation framework, right now we only care about the json_validator,
We need to verify each block's result ok is true, and the meta.output_path and 
meta.audio_path exist, and the file exists.



## Project Structure refine
Currently the {project_name}_burn.mp4 and {project_name}_final.mp4 are in the _work
folder, but they are final videos, re-name them to the {project_name}_nobgm.mp4 and
{project_name}.mp4, store outside the _work folder, just flat in the project folder,
and after the concat job, delete the _work folder.


## customize the character
Currently the `AUDIO_FISH_MODEL_ID`, `PICTURE_PATH` are read from .env. I want to read the project jsons block character field. get the information from the @character_config.json
And when concat the video, the @add_picture.py procedure will read the picture address from 
blocks character field as well.

## add the gradio front-end
use gradio create this project front-end, we have 2 sub-pages, first is to create project, user select a character from @[character_config.json](../config/character_config.json), and input the script in multiple lines format,
similar like @project_json_generator.py, and click create button to create new project.

The second sub-page need select a project from project folder, and it will display the config of that project(line by line script), and add a sub-sub page to view raw json. when User click make full video, it will refer to @cli/generate.py, begin the pipeline, and the front-end will keep polling the result from json file, display each blocks progress(Audio, Video, finish, etc...)

## avoid re-submit the video
1. In @pipeline.py, check the db first, if there are any job currently pending, invoke the
worker finished the current job first, then run the pipeline, to avoid re-submit the video.
2. when pipeline are running, set the status of `start making` button processing, avoid user click twice.


## Add status in the entire project pipeline
I add a new enum `ProjectStatus` in schema.py, add a new field in project json.
when pipeline running, set the correspond status for user to track details. In gradio
front-end, add a progress bar to show the status as well. 3 steps bar, first indicate 
project created, second indicate processing, third indicate rendering, if finish, mark
green or finish in the progress bar. Discard the `pipeline_failed` field, if more than 3 times try failed, mark the `ProjectStatus` failed and the pipeline will skip the project.


## Modify the remotion method
modify the current /methods/remotion_animation/method.py, we get the image path and title 
from
block.extra_info, and inside the working block, if the video generation result exists, render the output video, and save the info into block.remotion_generation.
If the video generation result not exists, then keep pending the working block.
You need to modify the [FilterTikTokSlide.tsx](../videogen/methods/remotion_animation/remotion_project/src/FilterTikTokSlide.tsx)
and rest of the tsx as well, to support render image on top of the video, not the black background.


## modify the project generation logic in @gradio_app.py
In @gradio_app.py, when user click the `create project` button, we need to abstract the generation process into a file in pipeline folder, and add some new rules: specific character only if the line begin with "character_name": xxxx.
if the entire line is [Lx.png:picture title...], then it will be treated as a picture block to the previous line, add the information inside the "extra_info" field, add the "title" file, the "template" file = FilterTikTokSlide
"single_picture" field is the picture file name.


## add method_name in working_blocks.db
We may need multiple job in same block, so we need to add a field in working_blocks.db, @setup_database.py and @working_block_dao.py, 
and store the method_name, so we can know which method to use.
Modify the @global_worker.py, when create and reading the working block, add the method_name field. create the method based on the method_name.

# Feature Request: Add background_video support (global background video mode)

## Goal
Enable users to attach a global background video to a project.  
When a background video exists, the pipeline should skip text_to_video generation and instead extract a segment from the background video for each clip.  
The extracted segment duration should match the generated audio length for each ScriptBlock.

---

## Step 1 — Update schema.py
1. Add a new optional field to Project or ScriptBlock (depending on current design):
background_video: Optional[str] = None



2. Ensure that this field is serialized and deserialized in the JSON correctly.

---

## Step 2 — Update gradio_app.py UI
1. Add a new UI component that allows the user to upload or choose a background video.
2. After user confirms, store the path in the project's JSON using the new `background_video` field.
3. Make sure loading an existing project correctly shows the current background video.

---

## Step 3 — Modify the pipeline flow
Inside the main pipeline execution logic (where ScriptBlock → WorkingBlocks are constructed):

1. Detect whether the project has `background_video`.
2. If background_video is set:
- DO NOT create a `text_to_video` step.
- Instead insert a new step: `"extract_background_segment"`.

Example:
tts → extract_background_segment → overlays → compose
   

3. If background_video is NOT set:
   - Keep the existing pipeline:

tts → text_to_video → overlays → compose


---

## Step 4 — Implement extract_background_segment method
Create a new method somewhere in `/pipeline/methods/` (follow existing convention).

Suggested name:

extract_background_segment_method()

 Compute start_time based on cumulative previous clip durations OR 0.0 if you want sequential slices.
 Use ffmpeg to extract:

ffmpeg -i background.mp4 -ss {start} -to {end} -c copy output.mp4

4. Save the output path to ScriptBlock.video_generation or a dedicated field.

---

## Step 5 — Update compose step
Ensure compose step uses:
- extracted background segment
- overlay layers (explain / character)
- audio track

---

## Requirements
- DO NOT break existing pipeline or text_to_video mode.
- The code must be backward compatible.
- The field name should be `background_video` (use consistent naming everywhere).
- The implementation should be easy to extend later (for motion/background registry).

---

## Deliverables
- schema.py updated
- gradio_app UI updated
- pipeline builder modified (conditional sequence)
- new extract_background_segment method implemented
- unit path or json examples updated if necessary


