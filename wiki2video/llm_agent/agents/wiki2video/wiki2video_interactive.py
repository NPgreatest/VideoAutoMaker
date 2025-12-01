import json
import re
from typing import Any, Dict, Optional, List

from wiki2video.llm_agent.agents.utils.script_normalizer import normalize_script
from wiki2video.llm_agent.agents.utils.wiki_fetcher import WikiFetcherAndCleanerWorker
from wiki2video.llm_agent.utils.markdown_loader import MarkdownPromptLoader
from wiki2video.llm_engine import get_engine

loader = MarkdownPromptLoader()


def _print_step(title: str):
    print(f"\n🔷 {title}")
    print("────────────────────────────────────")


async def _ask_llm(text: str, temperature=0.3, max_tokens=2000) -> str:
    return get_engine().ask_text(text, temperature=temperature, max_tokens=max_tokens).strip()


def _render_prompt(category: str, key: str, **kwargs) -> str:
    template = loader.load_from_registry(category, key)
    try:
        return template.format(**kwargs)
    except KeyError as exc:
        missing = exc.args[0]
        raise KeyError(f"Prompt 模板缺少变量: {missing}") from exc


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

    async def run_full(self, wiki_input: str, project_name: str) -> tuple[str, str]:

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
        template = loader.load_from_registry("wiki_direction_extractor", "default")
        prompt_text = template.replace(
            "{WIKI_JSON}", json.dumps(cleaned["sections"], ensure_ascii=False)
        )

        direction_raw = await _ask_llm(prompt_text)
        direction_obj = extract_json(direction_raw)

        print(f"✓ Direction title: {direction_obj.get('title', 'N/A')}")
        global_context = direction_obj.get("visual_context", "")

        # -------------------------------------
        # Step 3: Generate Full Script
        # -------------------------------------
        _print_step("3. Generating Narrative Script")
        script_prompt = _render_prompt(
            "script_structure",
            "wiki_solo_narrative",
            USER_SELECTED_DIRECTION_JSON=direction_raw,
            CLEANED_TEXT=cleaned["clean_text"],
        )
        script_raw = await _ask_llm(script_prompt)
        print("✓ Script draft generated")

        # -------------------------------------
        # Step 4: Insert Image Markers
        # -------------------------------------
        _print_step("4. Inserting Image Markers")
        insert_prompt = _render_prompt(
            "insert_image",
            "local",
            SCRIPT_TEXT=script_raw,
            IMAGE_SUMMARY=cleaned["images"],
        )
        script_final = await _ask_llm(insert_prompt)
        print("✓ Images inserted")

        # -------------------------------------
        # Step 5: Normalize Script
        # -------------------------------------
        _print_step("5. Finalizing Script")
        normalized_script = normalize_script(script_final)
        print("✓ Script normalized")

        print("\n✨ Done. Script + Global Context generated.\n")

        return normalized_script, global_context
