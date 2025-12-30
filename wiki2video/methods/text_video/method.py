# text_video/method.py
from __future__ import annotations
import json
import subprocess
import uuid
from pathlib import Path
from datetime import datetime, UTC
from dacite import from_dict

from wiki2video.methods.base import BaseMethod
from wiki2video.methods.registry import register_method
from wiki2video.methods.text_video.constants import FORMATS
from .api_router import get_provider
from wiki2video.llm_engine import get_engine
from wiki2video.core.working_block import WorkingBlock, WorkingBlockStatus
from wiki2video.core.paths import get_project_json_path
from wiki2video.schema.action_spec import ActionSpec
from wiki2video.schema.generation_result_schema import GenerationResult
from wiki2video.schema.schema_registry import get_schema
from wiki2video.core.path_utils import get_action_output_dir, get_output_file_path
from ...config.config_vars import WORKINGBLOCK_POLLING_COUNT_MAX


@register_method
class TextVideo(BaseMethod):
    NAME = "text_video"
    OUTPUT_KIND = "video"

    def __init__(self):
        super().__init__()

    def generate_prompt(self, text: str, global_context: str | None = "", project_id: str | None = "") -> str:
        """
        Convert a line of dialogue into a vivid cinematic scene prompt for text-to-video models.
        """
        engine = get_engine()
        context_block = (
            f"\nGlobal context for the video: {global_context.strip()}"
            if global_context
            else project_id
        )

        content = engine.ask_template(
            template_ref="text_video.cinematic_prompt",
            variables={
                "SCRIPT_TEXT": text.strip(),
                "GLOBAL_CONTEXT_BLOCK": context_block,
            },
            temperature=0.6,
            max_tokens=500,
        )

        prompt = "\n".join(
            l for l in content.splitlines() if not l.strip().lower().startswith("title:")
        ).strip()

        return prompt


    def run(self, spec: ActionSpec) -> WorkingBlock:
        """
        创建 WorkingBlock（不执行任务）
        """
        now = datetime.now(UTC).isoformat(timespec="seconds") + "Z"

        spec.config = spec.config or {}
        spec.config.setdefault("project_id", "default")

        return WorkingBlock(
            id=str(uuid.uuid4()),
            project_id=spec.config.get("project_id", "default"),
            method_name=self.NAME,
            status=WorkingBlockStatus.PENDING,
            prev_ids=[],
            output_path=None,
            config_json=json.dumps(spec.config),
            result_json="",
            create_time=now,
        )

    def poll(self, wb: WorkingBlock) -> GenerationResult:
        provider = get_provider()

        try:
            config_dict = json.loads(wb.config_json)
            schema_class = get_schema(self.NAME)
            config = from_dict(schema_class, config_dict)

            # 读取 request_id
            request_id = config_dict.get("request_id")
            if wb.polling_count >= WORKINGBLOCK_POLLING_COUNT_MAX - 1:
                print("Polling time exceeded, resetting request_id")
                wb.polling_count = 0
                request_id = None

            # ============ Step 1: 提交任务 ============
            if not request_id:
                if not config.prompt:
                    config.prompt = self.generate_prompt(config.text, config.global_context, wb.project_id)
                    config_dict["prompt"] = config.prompt

                # 解析项目 video 格式
                project_id = wb.project_id
                project_cfg_path = get_project_json_path(project_id)

                image_size = "1280x720"
                if project_cfg_path.exists():
                    with open(project_cfg_path) as f:
                        pj = json.load(f)
                        fmt = pj.get("size", "landscape")
                        image_size = FORMATS.get(fmt, "1280x720")
                print(f"[TEXT_VIDEO] Submitting video with size {image_size}")
                request_id = provider["submit"](config.prompt, image_size)

                if not request_id:
                    wb.status = WorkingBlockStatus.ERROR
                    return GenerationResult(
                        status=WorkingBlockStatus.ERROR,
                        output_path=None,
                        duration_sec=None,
                        error="Submit failed"
                    )

                config_dict["request_id"] = request_id
                wb.config_json = json.dumps(config_dict)

                return GenerationResult(
                    status=WorkingBlockStatus.PENDING,
                    output_path=None,
                    duration_sec=None,
                    error=None,
                )
            # ============ Step 2: 轮询状态 ============
            resp = provider["check"](request_id)
            status = resp["status"]
            op = resp.get("operation")

            # ⏳ 等待中
            if status == "wait":
                return GenerationResult(
                    status=WorkingBlockStatus.PENDING,
                    output_path=None,
                    duration_sec=None,
                    error=None,
                )

            # ❌ 错误 → 自动重试
            if status == "error":
                print("[TEXT_VIDEO] Video Generation Error occurred, resetting request_id")
                config_dict.pop("request_id", None)
                wb.config_json = json.dumps(config_dict)
                wb.status = WorkingBlockStatus.PENDING
                wb.polling_count = 0
                wb.error_count += 1
                return GenerationResult(
                    status=WorkingBlockStatus.PENDING,
                    output_path=None,
                    duration_sec=None,
                    error="AutoRetry: generation failed"
                )

            # 🎉 成功 → 下载视频
            if status == "success":
                print("[TEXT_VIDEO] Video Generation Success")

                url = provider["extract_url"](op)
                if not url:
                    wb.status = WorkingBlockStatus.ERROR
                    return GenerationResult(
                        status=WorkingBlockStatus.ERROR,
                        output_path=None,
                        duration_sec=None,
                        error="No video URL",
                    )

                block_id = wb.block_id or config_dict.get("target_name", wb.id)
                action_dir = get_action_output_dir(
                    wb.project_id, block_id, wb.method_name, wb.id
                )
                output_path = get_output_file_path(action_dir, block_id, "mp4")

                provider["download"](url, output_path)



                # 时长
                result_probe = subprocess.run(
                    ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                     "-of", "default=noprint_wrappers=1:nokey=1", str(output_path)],
                    capture_output=True, text=True
                )
                try:
                    duration = float(result_probe.stdout.strip())
                except:
                    duration = None

                wb.status = WorkingBlockStatus.SUCCESS
                wb.output_path = str(output_path)
                wb.result_json = json.dumps({
                    "status": "success",
                    "output_path": wb.output_path,
                    "duration": duration,
                    "request_id": request_id,
                    "prompt": config.prompt,
                })

                return GenerationResult(
                    status=WorkingBlockStatus.SUCCESS,
                    output_path=wb.output_path,
                    duration_sec=duration,
                    error=None,
                )

            # 理论不会走到这里
            return GenerationResult(
                status=WorkingBlockStatus.ERROR,
                output_path=None,
                duration_sec=None,
                error="Unknown status",
            )

        except Exception as e:
            wb.status = WorkingBlockStatus.ERROR
            return GenerationResult(
                status=WorkingBlockStatus.ERROR,
                output_path=None,
                duration_sec=None,
                error=str(e)
            )
