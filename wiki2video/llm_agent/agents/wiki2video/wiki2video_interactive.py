import json
import re
from typing import Any

from wiki2video.llm_agent.agents.utils.script_normalizer import normalize_script
from wiki2video.llm_agent.agents.utils.wiki_fetcher import WikiFetcherAndCleanerWorker
from wiki2video.llm_engine import get_engine


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
        direction_raw = self.engine.ask_template(
            template_ref="wiki_direction_extractor.default",
            variables={
                "WIKI_JSON": json.dumps(cleaned["sections"], ensure_ascii=False)
            },
            temperature=0.3,
            max_tokens=20000,
        )
        print(direction_raw)
        direction_obj = extract_json(direction_raw)

        print(f"✓ Direction title: {direction_obj.get('title', 'N/A')}")
        global_context = direction_obj.get("visual_context", "")

        # -------------------------------------
        # Step 3: Generate Full Script
        # -------------------------------------
        _print_step("3. Generating Narrative Script")
        script_raw = self.engine.ask_template(
            template_ref="script_structure.wiki_solo_narrative",
            variables={
                "USER_SELECTED_DIRECTION_JSON": direction_raw,
                "CLEANED_TEXT": cleaned["clean_text"],
            },
            temperature=0.35,
            max_tokens=20000,
        )
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
