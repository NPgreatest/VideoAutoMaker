import json
import re
from typing import Any
from jinja2 import Template as JinjaTemplate

from wiki2video.llm_agent.agents.utils.script_normalizer import normalize_script
from wiki2video.llm_agent.agents.utils.wiki_fetcher import WikiFetcherAndCleanerWorker
from wiki2video.llm_engine import get_engine
from wiki2video.llm_engine.markdown_loader import MarkdownPromptLoader


def _print_step(title: str):
    print(f"\n🔷 {title}")
    print("────────────────────────────────────")


def extract_json(raw: str) -> dict[Any, Any] | None:
    if not isinstance(raw, str) or not raw.strip():
        return {}
    text = raw.strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    json_candidates = re.findall(r"\{.*?\}", text, flags=re.DOTALL)
    for jc in json_candidates:
        try:
            return json.loads(jc)
        except Exception:
            continue
    return {}


class Wiki2VideoInteractiveOrchestrator:

    def __init__(self):
        self.fetcher_cleaner = WikiFetcherAndCleanerWorker()
        self.engine = get_engine()

    async def run_full(self, wiki_input: str, project_name: str, language: str = "en", duration: float = 1.0) -> tuple[str, str]:

        # -------------------------------------
        # Step 1: Fetch + Clean Wikipedia
        # -------------------------------------
        _print_step("1. Fetching & Cleaning Wikipedia Content")
        cleaned = self.fetcher_cleaner.run(wiki_input, project_name)
        print(f"✓ Sections: {len(cleaned['sections'])} | Images: {len(cleaned['images'])}")

        # -------------------------------------
        # Step 2: Generate Documentary Direction
        # -------------------------------------
        _print_step("2. Extracting Documentary Direction")
        
        # Load direction extractor template and modify based on language
        loader = MarkdownPromptLoader()
        direction_template = loader.load_from_registry("wiki_direction_extractor", "default")
        
        # Add language instruction if Chinese
        if language == "zh":
            # Add instruction to generate Chinese hook and title
            direction_template += "\n\nIMPORTANT LANGUAGE REQUIREMENT:\n"
            direction_template += "- All output (title, hook, storyline, visual_context) MUST be in Chinese (简体中文).\n"
            direction_template += "- The hook must be a dramatic or curiosity-driven first line in Chinese.\n"
            direction_template += "- The title must be in Chinese.\n"
        
        # Render direction template
        jinja_direction_template = JinjaTemplate(direction_template)
        direction_prompt = jinja_direction_template.render(
            WIKI_JSON=json.dumps(cleaned["sections"], ensure_ascii=False)
        )
        
        direction_raw = self.engine.ask_text(direction_prompt, temperature=0.3, max_tokens=20000)
        print(direction_raw)
        direction_obj = extract_json(direction_raw)

        print(f"✓ Direction title: {direction_obj.get('title', 'N/A')}")
        global_context = direction_obj.get("visual_context", "")

        # -------------------------------------
        # Step 3: Generate Full Script
        # -------------------------------------
        _print_step("3. Generating Narrative Script")
        
        # Calculate target lines based on duration (assuming 6.5 seconds per line on average)
        target_lines = max(10, int(duration * 60 / 6.5))
        min_lines = max(5, int(target_lines * 0.7))
        max_lines = int(target_lines * 1.3)
        
        # Load template and modify it dynamically
        template = loader.load_from_registry("script_structure", "wiki_solo_narrative")
        
        # Replace the Total length line with dynamic duration-based instruction
        template = re.sub(
            r"Total length:.*?\(\≈.*?lines\)\.",
            f"Total length: {duration:.1f} minutes (≈{min_lines}-{max_lines} lines).",
            template,
            flags=re.MULTILINE
        )
        
        # Update language/style instructions based on language parameter
        if language == "zh":
            template = re.sub(
                r"Global English suitable for TikTok/YouTube audiences\.",
                "适合中文短视频平台（抖音、B站等）的中文叙事风格。",
                template
            )
            template = re.sub(
                r"short-form English storytelling scripts",
                "短篇中文叙事脚本",
                template
            )
            template = re.sub(
                r"Each line should be 5–8 seconds of spoken English",
                "每行应该是5-8秒的中文旁白",
                template
            )
            template = re.sub(
                r"English storytelling scripts for TikTok and YouTube Shorts",
                "中文叙事脚本，适用于抖音和B站等短视频平台",
                template
            )
            # Modify hook instruction for Chinese: if hook is in English, translate it to Chinese
            template = re.sub(
                r"A\. One-line Hook \(first line\)\n- Use the hook from the selected direction exactly as the first line\.\n- Do not rewrite, expand, or modify it\.",
                "A. One-line Hook (first line)\n- The first line MUST be in Chinese (简体中文).\n- If the hook in the selected direction is in English, translate it to Chinese while preserving its dramatic or curiosity-driven tone.\n- If the hook is already in Chinese, use it exactly as provided.\n- The hook should be a compelling opening line that grabs attention.",
                template
            )
            template = re.sub(
                r"The hook provided in the selected direction MUST be the first line\.",
                "The first line MUST be in Chinese. If the hook in the direction is in English, translate it to Chinese while maintaining its dramatic impact.",
                template
            )
        
        # Render template with variables using Jinja2
        jinja_template = JinjaTemplate(template)
        final_prompt = jinja_template.render(
            USER_SELECTED_DIRECTION_JSON=direction_raw,
            CLEANED_TEXT=cleaned["clean_text"],
        )
        
        script_raw = self.engine.ask_text(final_prompt, temperature=0.35, max_tokens=20000)
        print(script_raw)
        print("✓ Script draft generated")

        # -------------------------------------
        # Step 4: Insert Image Markers
        # -------------------------------------
        _print_step("4. Inserting Image Markers")
        script_final = self.engine.ask_template(
            template_ref="insert_image.local",
            variables={
                "SCRIPT_TEXT": script_raw,
                "IMAGE_SUMMARY": json.dumps(cleaned["images"], ensure_ascii=False),
            },
            temperature=0.2,
            max_tokens=20000,
        )
        print(script_final)
        print("✓ Images inserted")

        # -------------------------------------
        # Step 5: Normalize Script
        # -------------------------------------
        _print_step("5. Finalizing Script")
        normalized_script = normalize_script(script_final)
        print("✓ Script normalized")

        print("\n✨ Done. Script + Global Context generated.\n")

        return normalized_script, global_context
