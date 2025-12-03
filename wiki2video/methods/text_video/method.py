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
from wiki2video.pipeline.working_block import WorkingBlock, WorkingBlockStatus
from wiki2video.schema.action_spec import ActionSpec
from wiki2video.schema.generation_result_schema import GenerationResult
from wiki2video.schema.schema_registry import get_schema
from wiki2video.pipeline.path_utils import get_action_output_dir, get_output_file_path


@register_method
class TextVideo(BaseMethod):
    NAME = "text_video"
    OUTPUT_KIND = "video"

    def __init__(self):
        super().__init__()

    def generate_prompt(self, text: str, global_context: str | None = None) -> str:
        engine = get_engine()

        system_prompt = (
            "You are an expert cinematic visual director...\n"
            "Focus only on what the camera would show...\n"
        )
        context_block = f"\nGlobal context: {global_context.strip()}" if global_context else ""

        user_prompt = f"Input:\n{text.strip()}{context_block}\n\nOutput:"

        res = engine.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )
        print(res)
        return res["content"].strip()

    def run(self, spec: ActionSpec) -> WorkingBlock:
        """
        创建 WorkingBlock（不执行任务）
        """
        now = datetime.now(UTC).isoformat(timespec="seconds") + "Z"

        return WorkingBlock(
            id=str(uuid.uuid4()),
            project_name=spec.config.get("project_name", "default"),
            method_name=self.NAME,
            status=WorkingBlockStatus.PENDING,
            prev_ids=[],
            output_path=None,
            config_json=json.dumps(spec.config),
            result_json="",
            create_time=now,
            modify_time=now,
        )

    def poll(self, wb: WorkingBlock) -> GenerationResult:
        provider = get_provider()

        try:
            config_dict = json.loads(wb.config_json)
            schema_class = get_schema(self.NAME)
            config = from_dict(schema_class, config_dict)

            # 读取 request_id
            request_id = config_dict.get("request_id")

            # ============ Step 1: 提交任务 ============
            if not request_id:
                if not config.prompt:
                    config.prompt = self.generate_prompt(config.text, config.global_context)
                    config_dict["prompt"] = config.prompt

                # 解析项目 video 格式
                workdir = Path(config_dict.get("workdir", "."))
                project_root = workdir.resolve()
                project_name = wb.project_name
                project_cfg_path = workdir / "project" / project_name / f"{project_name}.json"

                image_size = "1280x720"
                if project_cfg_path.exists():
                    with open(project_cfg_path) as f:
                        pj = json.load(f)
                        fmt = pj.get("size", "landscape")
                        image_size = FORMATS.get(fmt, "1280x720")

                request_id = provider["submit"](config.prompt, image_size)

                if not request_id:
                    wb.status = WorkingBlockStatus.ERROR
                    return GenerationResult(
                        status=WorkingBlockStatus.ERROR,
                        error="Submit failed"
                    )

                config_dict["request_id"] = request_id
                wb.config_json = json.dumps(config_dict)

                return GenerationResult(status=WorkingBlockStatus.PENDING)

            # ============ Step 2: 轮询状态 ============
            resp = provider["check"](request_id)
            status = resp["status"]
            raw_resp = resp["raw"]

            # ⏳ 等待中
            if status == "wait":
                return GenerationResult(status=WorkingBlockStatus.PENDING)

            # ❌ 错误 → 自动重试（清除 request_id）
            if status == "error":
                config_dict.pop("request_id", None)
                wb.config_json = json.dumps(config_dict)
                wb.status = WorkingBlockStatus.PENDING
                return GenerationResult(
                    status=WorkingBlockStatus.PENDING,
                    error="AutoRetry: generation failed"
                )

            # 🎉 成功 → 下载视频
            if status == "success":
                url = provider["extract_url"](raw_resp)
                if not url:
                    wb.status = WorkingBlockStatus.ERROR
                    return GenerationResult(status=WorkingBlockStatus.ERROR, error="No video URL")

                # 输出路径
                workdir = Path(config_dict.get("workdir", "."))
                project_root = workdir.resolve()
                block_id = wb.block_id or config_dict.get("target_name", wb.id)
                action_dir = get_action_output_dir(project_root, wb.project_name, block_id, wb.method_name, wb.id)
                output_path = get_output_file_path(action_dir, "mp4")

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
                    duration_sec=duration
                )

            # 理论不会走到这里
            return GenerationResult(status=WorkingBlockStatus.ERROR, error="Unknown status")

        except Exception as e:
            wb.status = WorkingBlockStatus.ERROR
            return GenerationResult(
                status=WorkingBlockStatus.ERROR,
                error=str(e)
            )
