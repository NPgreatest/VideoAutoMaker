from typing import Any

from videogen.llm_agent.agents.utils.wiki_fetcher import WikiFetcherAndCleanerWorker
from videogen.llm_agent.utils.markdown_loader import MarkdownPromptLoader
from videogen.llm_engine import get_engine

loader = MarkdownPromptLoader()

async def ask_llm_by_prompt(text):
    engine = get_engine()
    res = engine.ask_text(
        text,
        temperature=0.3,
        max_tokens=180
    )
    return res.strip()

def _render(template: str, **kwargs: Any) -> str:
    try:
        return template.format(**kwargs)
    except KeyError as exc:  # pragma: no cover - 配置错误
        missing = exc.args[0]
        raise KeyError(f"Prompt 模板缺少变量: {missing}") from exc


class Wiki2VideoInteractiveOrchestrator:

    def __init__(self, llm, mcp):
        self.fetcher_cleaner = WikiFetcherAndCleanerWorker()

        # 保存状态，让第二步使用
        self._cached_sections = None

    # =============================================
    # STEP 1: Fetch Wiki + Clean + Generate Directions
    # =============================================
    async def step_prepare(self, wiki_input: str, project_name: str):
        """
        第一阶段：
        1. fetch wiki
        2. clean text
        3. summarize sections
        4. extract images
        5. generate directions
        6. 返回方向供前端 UI 展示给用户
        """

        cleaned = await self.fetcher_cleaner.run(wiki_input, project_name)
        print(f"[DEBUG] cleaned: {cleaned}")


        get_direction_prompt = loader.load_from_registry("wiki_direction_extractor", "default")
        write_script_text = _render(get_direction_prompt, WIKI_JSON = cleaned["sections"])
        directions = await ask_llm_by_prompt(write_script_text)

        self._cached_sections = {
            "clean_text": cleaned["clean_text"],
            "images": cleaned["images"],
            "sections": cleaned["sections"],
            "directions": directions,       # 给 UI 展示选择
        }

        print(f"[DEBUG] directions: {directions}")
        return self._cached_sections

    # =============================================
    # STEP 2: User selects a direction → write script → search images → insert markers
    # =============================================
    async def step_generate_script(self, selected_direction: int):
        """
        用户选择 direction 后：
        1. script_writer
        2. image_selector
        3. image_inserter
        """

        if self._cached_sections is None:
            raise RuntimeError("Must run step_prepare() before step_generate_script()")

        # write the script
        selected_str = self._cached_sections["directions"][selected_direction]
        prompt = loader.load_from_registry("script_structure", "wiki_solo_narrative")
        write_script_text = _render(prompt, USER_SELECTED_DIRECTION_JSON = selected_str, CLEANED_TEXT=self._cached_sections["clean_text"]) # WIKI_JSON should be str
        script_raw = await ask_llm_by_prompt(write_script_text)
        print(f"[DEBUG] script_raw: {script_raw}")

        # insert images
        prompt = loader.load_from_registry("insert_image", "local")
        insert_image_text = _render(prompt, SCRIPT_TEXT = script_raw, IMAGE_SUMMARY= self._cached_sections["images"]) # WIKI_JSON should be str

        script_final = await  ask_llm_by_prompt(insert_image_text)
        print(f"[DEBUG] script_final: {script_final}")

        return script_final


