import json
from typing import Any, Dict, Optional, List

from wiki2video.llm_agent.agents.utils.script_normalizer import normalize_script
from wiki2video.llm_agent.agents.utils.wiki_fetcher import WikiFetcherAndCleanerWorker
from wiki2video.llm_agent.utils.markdown_loader import MarkdownPromptLoader
from wiki2video.llm_engine import get_engine

# 全局 loader
loader = MarkdownPromptLoader()


async def _ask_llm(text: str, temperature=0.3, max_tokens=2000) -> str:
    return get_engine().ask_text(text, temperature=temperature, max_tokens=max_tokens).strip()

def _render_prompt(category: str, key: str, **kwargs) -> str:
    template = loader.load_from_registry(category, key)
    try:
        return template.format(**kwargs)
    except KeyError as exc:
        missing = exc.args[0]
        raise KeyError(f"Prompt 模板缺少变量: {missing}") from exc


class Wiki2VideoInteractiveOrchestrator:

    def __init__(self):
        self.fetcher_cleaner = WikiFetcherAndCleanerWorker()

    async def run_full(self, wiki_input: str, project_name: str) -> str:
        """
        直接返回最终剧本：
        1. fetch & clean
        2. auto extract documentary direction (no choosing)
        3. script generation
        4. insert images
        """
        cleaned = self.fetcher_cleaner.run(wiki_input, project_name)
        print(f"input {json.dumps(cleaned['sections'], ensure_ascii=False)}")

        # ---- Step A: generate documentary direction (no options) ----
        template = loader.load_from_registry("wiki_direction_extractor", "default")
        prompt_text = template.replace("{WIKI_JSON}", json.dumps(cleaned["sections"], ensure_ascii=False))
        direction = await _ask_llm(prompt_text)
        print("[DEBUG] chosen_direction:", direction)

        # ---- Step B: generate script ----
        script_prompt = _render_prompt(
            "script_structure",
            "wiki_solo_narrative",
            USER_SELECTED_DIRECTION_JSON=direction,   # now always ONE direction
            CLEANED_TEXT=cleaned["clean_text"],
        )
        script_raw = await _ask_llm(script_prompt)
        print("[DEBUG] script_raw:", script_raw)

        # ---- Step C: insert images ----
        insert_prompt = _render_prompt(
            "insert_image",
            "local",
            SCRIPT_TEXT=script_raw,
            IMAGE_SUMMARY=cleaned["images"],
        )
        script_final = await _ask_llm(insert_prompt)
        print("[DEBUG] script_final:", script_final)

        normalized_script = normalize_script(script_final)
        print(
            f"[DEBUG] normalized script:\n{normalize_script}"
        )

        return normalized_script
