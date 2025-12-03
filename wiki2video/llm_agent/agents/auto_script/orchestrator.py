"""AutoScriptAgent：串联 Prompt1/Prompt2 生成短视频剧本。"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Any, Dict

from ....llm_engine.client import LLMEngine, get_engine
from ...mcp.tools.image_search.tool import ImageSearchTool
from wiki2video.llm_engine.markdown_loader import MarkdownPromptLoader


@dataclass(slots=True)
class AutoScriptAgentResult:
    """Agent 输出的结构化结果。"""

    topic: str
    style: str
    background_info: str
    final_script: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AutoScriptAgent:
    """两阶段 Auto Script Agent：Prompt1(资料) → Prompt2(剧本)。"""

    PROMPT_1_CATEGORY = "info_query"
    PROMPT_1_DEFAULT_KEY = "default"
    PROMPT_2_CATEGORY = "script_structure"
    PROMPT_2_DEFAULT_KEY = "default"

    def __init__(
        self,
        *,
        engine: LLMEngine | None = None,
        prompt_loader: MarkdownPromptLoader | None = None,
    ) -> None:
        self.engine = engine or get_engine()
        self.prompt_loader = prompt_loader or MarkdownPromptLoader()

    def run(
        self,
        *,
        topic: str,
        style: str = None,
        prompt1_key: str | None = None,
        prompt2_key: str | None = None,
        project_name: str | None = None,
    ) -> AutoScriptAgentResult:
        topic = topic.strip()
        style = style.strip()

        if not topic:
            raise ValueError("AutoScriptAgent.run: topic 不能为空")

        background_template = self._get_prompt_template(
            self.PROMPT_1_CATEGORY, prompt1_key, self.PROMPT_1_DEFAULT_KEY
        )
        background_prompt = self._render(
            background_template,
            topic=topic,
            style=style,
        )
        background_info = self._ask_llm(background_prompt)
        self._log_llm_output("Prompt1 背景资料", background_info)

        script_template = self._get_prompt_template(
            self.PROMPT_2_CATEGORY, prompt2_key, self.PROMPT_2_DEFAULT_KEY
        )
        script_prompt = self._render(
            script_template,
            topic=topic,
            style=style,
            background_info=background_info,
        )
        final_script = self._ask_llm(script_prompt)
        self._log_llm_output("Prompt2 剧本", final_script)

        # 自动处理脚本中的图片标记
        if project_name:
            self._process_image_markers(final_script, project_name)

        return AutoScriptAgentResult(
            topic=topic,
            style=style,
            background_info=background_info.strip(),
            final_script=final_script.strip(),
        )

    # -------- helpers --------
    def _render(self, template: str, **kwargs: Any) -> str:
        try:
            return template.format(**kwargs)
        except KeyError as exc:  # pragma: no cover - 配置错误
            missing = exc.args[0]
            raise KeyError(f"Prompt 模板缺少变量: {missing}") from exc

    def _ask_llm(self, prompt: str) -> str:
        return self.engine.ask_text(prompt)

    def _log_llm_output(self, label: str, content: str, preview_len: int = 200) -> None:
        safe_content = (content or "").strip()
        if not safe_content:
            print(f"[AutoScriptAgent] {label} 输出为空。")
            return
        head = safe_content[:preview_len]
        tail = (
            safe_content[-preview_len:] if len(safe_content) > preview_len else ""
        )
        print(f"[AutoScriptAgent] {label} 输出片段（开头）:\n{head}")
        if tail:
            print(f"[AutoScriptAgent] {label} 输出片段（结尾）:\n{tail}")

    def _get_prompt_template(
        self, category: str, key: str | None, default_key: str
    ) -> str:
        selected_key = (key or default_key).strip()
        if not selected_key:
            raise ValueError("Prompt key 不能为空")
        return self.prompt_loader.load_from_registry(category, selected_key)

    def load_prompt_from_registry(self, category: str, key: str) -> str:
        """
        根据 registry.json 中的分类与 key 动态获取 prompt 模板路径。

        - 前端会读取 registry.json，展示 category-key 列表供用户选择。
        - 用户选择的 key 将回传到后端，后端调用此接口获得 Markdown 模板正文。
        - 当前任务仅定义接口，具体逻辑待后续迭代实现。
        """
        return self.prompt_loader.load_from_registry(category, key)

    def _process_image_markers(self, script: str, project_name: str) -> None:
        """
        解析脚本中的图片标记并自动搜索下载图片。
        
        图片标记格式: [filename: search query]
        例如: [TokenDiagram.png: token-to-ID mapping diagram]
        """
        # 匹配格式: [filename: search query]
        pattern = r'\[([^\]:]+):\s*([^\]]+)\]'
        matches = re.findall(pattern, script)
        
        if not matches:
            print("[AutoScriptAgent] 未发现图片标记，跳过图片搜索。")
            return
        
        print(f"[AutoScriptAgent] 发现 {len(matches)} 个图片标记，开始搜索下载...")
        image_tool = ImageSearchTool()
        
        for filename, search_query in matches:
            filename = filename.strip()
            search_query = search_query.strip()
            
            if not filename or not search_query:
                print(f"[AutoScriptAgent] ⚠️ 跳过无效的图片标记: [{filename}: {search_query}]")
                continue
            
            try:
                print(f"[AutoScriptAgent] 🔍 搜索图片: {search_query} → {filename}")
                result = image_tool.run({
                    "query": search_query,
                    "project_name": project_name,
                    "target_name": filename,
                })
                
                if "error" in result:
                    print(f"[AutoScriptAgent] ❌ 图片搜索失败 ({filename}): {result['error']}")
                else:
                    print(f"[AutoScriptAgent] ✅ 图片已保存: {result['best']}")
                    if result.get("alternatives"):
                        print(f"[AutoScriptAgent]   备选图片: {len(result['alternatives'])} 张")
                        
            except Exception as exc:
                print(f"[AutoScriptAgent] ❌ 处理图片标记失败 ({filename}): {exc}")
                continue
        
        print(f"[AutoScriptAgent] 图片处理完成。")


__all__ = ["AutoScriptAgent", "AutoScriptAgentResult"]
