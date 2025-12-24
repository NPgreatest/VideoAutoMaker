#!/usr/bin/env python3
from __future__ import annotations

import json
import uuid
from datetime import datetime, UTC
from pathlib import Path

from wiki2video.core.path_utils import get_action_output_dir, get_output_file_path
from wiki2video.core.working_block import WorkingBlock, WorkingBlockStatus
from wiki2video.llm_engine import get_engine
from wiki2video.methods.base import BaseMethod
from wiki2video.methods.registry import register_method
from wiki2video.schema.action_spec import ActionSpec
from wiki2video.schema.generation_result_schema import GenerationResult

from .schema import TextImageConfig


FORMATS = {
    "landscape": "1280x720",
    "tiktok": "720x1280",
}


@register_method
class TextImageMethod(BaseMethod):
    NAME = "text_image"
    OUTPUT_KIND = "image"

    def generate_prompt(self, text: str, global_context: str | None = "", project_id: str | None = "") -> str:
        """
        Convert narration text into a cinematic film-still prompt for text-to-image models.
        """
        source_text = (text or "").strip()
        if not source_text:
            raise ValueError("TextImageMethod requires either 'prompt' or 'text'.")

        engine = get_engine()
        context_block = (global_context or "").strip() or (project_id or "")

        content = engine.ask_template(
            template_ref="text_image.film_frame_prompt",
            variables={
                "SCRIPT_TEXT": source_text,
                "GLOBAL_CONTEXT_BLOCK": context_block,
            },
            temperature=0.5,
            max_tokens=400,
        )

        prompt = "\n".join(line.strip() for line in content.splitlines() if line.strip())
        return prompt

    def run(self, spec: ActionSpec) -> WorkingBlock:
        spec.config = spec.config or {}
        spec.config.setdefault("project_id", "default")
        spec.config.setdefault("workdir", ".")

        # Validate config structure early
        TextImageConfig(**spec.config)

        working_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat(timespec="seconds") + "Z"

        return WorkingBlock(
            id=working_id,
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
        try:
            config_dict = json.loads(wb.config_json or "{}")
            cfg = TextImageConfig(**config_dict)

            project_id = cfg.project_id or wb.project_id or "default"
            project_cfg_path = Path(config_dict.get("workdir", ".")) / "project" / project_id / f"{project_id}.json"

            image_size = "1280x720"
            if project_cfg_path.exists():
                with open(project_cfg_path) as f:
                    pj = json.load(f)
                    fmt = pj.get("size", "landscape")
                    image_size = FORMATS.get(fmt, "1280x720")
            cfg.size = image_size

            prompt = (cfg.prompt or "").strip()
            if not prompt:
                source_text = (cfg.text or "").strip()
                if not source_text:
                    raise ValueError("TextImageMethod requires either 'prompt' or 'text'.")
                prompt = self.generate_prompt(source_text, cfg.global_context, project_id)
                config_dict["prompt"] = prompt
                cfg.prompt = prompt

            provider = (cfg.provider or "siliconflow").lower()

            if provider == "openai":
                from .providers.openai_image_provider import openai_generate_image

                resp = openai_generate_image(prompt, cfg.negative_prompt, cfg.size)
                raise RuntimeError(resp.get("reason", "OpenAI text_image provider not implemented"))

            if provider == "google":
                from .providers.google_image_provider import google_generate_image

                image_bytes = google_generate_image(prompt, cfg.negative_prompt, cfg.size)
            elif provider == "siliconflow":
                from .providers.siliconflow_image_provider import siliconflow_generate_image

                image_bytes = siliconflow_generate_image(prompt, cfg.negative_prompt, cfg.size)
            else:
                raise ValueError(f"Unsupported text_image provider: {provider}")

            workdir = Path(cfg.workdir or ".").expanduser().resolve()
            block_id = cfg.target_name or wb.block_id or wb.id
            action_dir = get_action_output_dir(workdir, project_id, block_id, wb.method_name, wb.id)
            action_dir.mkdir(parents=True, exist_ok=True)
            output_path = get_output_file_path(action_dir, block_id, "png")
            output_path.write_bytes(image_bytes)

            wb.config_json = json.dumps(config_dict)

            wb.status = WorkingBlockStatus.SUCCESS
            wb.output_path = str(output_path)
            wb.result_json = json.dumps({
                "status": "success",
                "output_path": wb.output_path,
                "provider": provider,
                "prompt": prompt,
                "size": cfg.size,
            })

            return GenerationResult(
                status=WorkingBlockStatus.SUCCESS,
                output_path=str(output_path),
                duration_sec=None,
                error=None,
            )

        except Exception as exc:
            wb.status = WorkingBlockStatus.ERROR
            wb.result_json = json.dumps({"status": "error", "error": str(exc)})
            return GenerationResult(
                status=WorkingBlockStatus.ERROR,
                output_path=None,
                duration_sec=None,
                error=str(exc),
            )


__all__ = ["TextImageMethod"]
