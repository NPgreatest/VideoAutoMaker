import os
import re
import mwclient
import mwparserfromhell
import requests
from urllib.parse import urlparse, unquote

from ...utils.markdown_loader import MarkdownPromptLoader
from ....llm_engine.client import get_engine


loader = MarkdownPromptLoader()


async def summarize_section(text):
    prompt = loader.load_from_registry("wiki", "section_summary")
    engine = get_engine()

    res = engine.ask_text(
        prompt.format(text=text),
        temperature=0.3,
        max_tokens=180
    )
    return res.strip()


class WikiFetcherAndCleanerWorker:

    COMMONS = mwclient.Site("commons.wikimedia.org")
    ENWIKI = mwclient.Site("en.wikipedia.org")

    # ---------------------------
    # 工具函数：解析输入 URL 或标题
    # ---------------------------
    def normalize_title(self, user_input: str) -> str:
        if user_input.startswith(("http://", "https://")):
            parsed = urlparse(user_input)
            m = re.match(r"^/wiki/(.+)$", parsed.path)
            if not m:
                raise ValueError("Invalid Wikipedia URL")
            title = unquote(m.group(1)).replace("_", " ")
            return title
        return user_input.strip()

    # ---------------------------
    # 工具函数：从 wikicode 中提取纯文本
    # ---------------------------
    def clean_raw_text(self, wikicode):
        text = wikicode.strip_code()
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        return "\n".join(lines)

    # ---------------------------
    # 工具函数：提取 File: 图片
    # ---------------------------
    def extract_images(self, wikicode):
        imgs = []
        for node in wikicode.filter_wikilinks():
            title = str(node.title)
            if title.lower().startswith(("file:", "image:")):
                imgs.append({
                    "file_name": title.split(":", 1)[1],
                    "caption": str(node.text or "")
                })
        return imgs

    # ---------------------------
    # 文本清洗
    # ---------------------------
    def deep_clean_text(self, t: str) -> str:
        t = re.sub(r"<ref.*?>.*?</ref>", "", t, flags=re.DOTALL)
        t = re.sub(r"<ref[^>]*\s*/>", "", t)
        t = re.sub(r"\{\{.*?\}\}", "", t)
        t = re.sub(r"'{2,}", "", t)
        t = re.sub(r"\n{2,}", "\n", t)
        return t.strip()

    # ---------------------------
    # 获取图片真实 URL
    # ---------------------------
    def get_real_url(self, file_name):
        title = f"File:{file_name}"
        for site in (self.COMMONS, self.ENWIKI):
            try:
                data = site.api("query", prop="imageinfo", titles=title, iiprop="url")
                pages = data.get("query", {}).get("pages", {})
                for p in pages.values():
                    info = p.get("imageinfo")
                    if info:
                        return info[0].get("url")
            except Exception:
                continue
        return None

    # ---------------------------
    # 下载图片
    # ---------------------------
    def download_image(self, url: str, local_path: str):
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            ),
            "Referer": "https://en.wikipedia.org/"
        }
        try:
            resp = requests.get(url, headers=headers, timeout=20)
            if resp.status_code == 200:
                with open(local_path, "wb") as f:
                    f.write(resp.content)
                return True
        except Exception:
            pass

        return False


    # ---------------------------
    # 主流程：抓取 + 清理 + 总结 + 下载图片
    # ---------------------------
    async def run(self, user_input: str, project_name: str):
        # 创建图片文件夹路径
        image_dir = f"./project/{project_name}/image_candidates"
        os.makedirs(image_dir, exist_ok=True)

        title = self.normalize_title(user_input)
        site = mwclient.Site("en.wikipedia.org")
        page = site.pages[title]

        if page.redirect:
            page = page.resolve_redirect()

        raw = page.text()
        wikicode = mwparserfromhell.parse(raw)
        sections = wikicode.get_sections(include_lead=True, flat=True)

        structured = []
        all_images = []
        all_text = []

        for sec in sections:
            heading_nodes = sec.filter_headings()
            heading = heading_nodes[0].title.strip() if heading_nodes else "Introduction"

            raw_text = self.clean_raw_text(sec)
            cleaned = self.deep_clean_text(raw_text)

            # summary
            summary = await summarize_section(cleaned)
            wc = len(cleaned.split())

            # process images
            sec_imgs = []
            for img in self.extract_images(sec):
                file_name = img["file_name"]
                caption = self.deep_clean_text(img["caption"])

                url = self.get_real_url(file_name)
                if not url:
                    continue

                # 生成本地文件路径
                local_path = os.path.join(image_dir, file_name)

                # 下载文件
                self.download_image(url, local_path)

                img_obj = {
                    "file_name": file_name,
                    "caption": caption,
                    "url": url,
                    "local_path": local_path,
                    "section": heading
                }

                sec_imgs.append(img_obj)
                all_images.append(img_obj)

            structured.append({
                "heading": heading,
                "summary": summary,
                "word_count": wc,
                "images": sec_imgs
            })

            all_text.append(cleaned)

        return {
            "clean_text": "\n\n".join(all_text),
            "images": all_images,
            "sections": structured
        }
