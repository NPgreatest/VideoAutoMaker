import re
import mwclient
import mwparserfromhell
from urllib.parse import urlparse, unquote
from pathlib import Path
import requests
import time

from ....llm_engine.client import get_engine
from ..utils.svg_converter import sanitize_filename, ensure_non_svg


class WikiFetcherAndCleanerWorker:

    COMMONS = mwclient.Site("commons.wikimedia.org")
    ENWIKI = mwclient.Site("en.wikipedia.org")

    def __init__(self) -> None:
        self.engine = get_engine()

    # ---------------------------
    # normalize title
    # ---------------------------
    def normalize_title(self, user_input: str) -> str:
        print(f"\n🔵 STEP: normalize_title('{user_input}')")
        if user_input.startswith(("http://", "https://")):
            parsed = urlparse(user_input)
            m = re.match(r"^/wiki/(.+)$", parsed.path)
            if not m:
                raise ValueError("Invalid Wikipedia URL")
            title = unquote(m.group(1)).replace("_", " ")
            print(f"🟡 Normalized title from URL = {title}")
            return title
        print(f"🟡 Normalized title = {user_input.strip()}")
        return user_input.strip()

    # ---------------------------
    def clean_raw_text(self, wikicode):
        text = wikicode.strip_code()
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        return "\n".join(lines)

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
    def deep_clean_text(self, t: str) -> str:
        t = re.sub(r"<ref.*?>.*?</ref>", "", t, flags=re.DOTALL)
        t = re.sub(r"<ref[^>]*\s*/>", "", t)
        t = re.sub(r"\{\{.*?\}\}", "", t)
        t = re.sub(r"'{2,}", "", t)
        t = re.sub(r"\n{2,}", "\n", t)
        return t.strip()

    # ---------------------------
    def get_real_url(self, file_name):
        print(f"    🔍 Resolving image URL for: {file_name}")
        title = f"File:{file_name}"
        for site in (self.COMMONS, self.ENWIKI):
            try:
                data = site.api("query", prop="imageinfo", titles=title, iiprop="url")
                pages = data.get("query", {}).get("pages", {})
                for p in pages.values():
                    info = p.get("imageinfo")
                    if info:
                        url = info[0].get("url")
                        print(f"    🟡 Found URL = {url}")
                        return url
            except Exception as e:
                print(f"    🔴 Error fetching from site: {e}")
                continue
        print("    🔴 No URL resolved!")
        return None

    # ---------------------------
    def summarize_section(self, text: str):
        print(f"    🔵 STEP: summarize_section (len={len(text)} chars)")
        try:
            summary = self.engine.ask_template(
                template_ref="wiki_summary.section_summary",
                variables={"SECTION_TEXT": text},
                temperature=0.3,
                max_tokens=180,
            )
            print(f"    🟡 Summary done (len={len(summary)} chars)")
            return summary
        except Exception as e:
            print(f"    🔴 [ERROR] LLM generation failed: {e}")
            return ""

    # ---------------------------
    def download_image(self, url, out_path: Path):
        print(f"    📥 Downloading {url} -> {out_path}")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://en.wikipedia.org/"
        }
        try:
            r = requests.get(url, headers=headers, timeout=15)
            r.raise_for_status()
            with open(out_path, "wb") as f:
                f.write(r.content)
            print(f"    🟡 Image saved.")
            return True
        except Exception as e:
            print(f"    🔴 [Image] Download error: {e}")
            return False

    # ---------------------------
    # 主流程
    # ---------------------------
    def run(self, user_input: str, project_name: str):
        print("\n==============================")
        print("   🚀 WikiFetcher RUN START")
        print("==============================\n")

        t0 = time.time()

        title = self.normalize_title(user_input)

        print(f"\n🔵 STEP: Fetching page '{title}'")
        site = mwclient.Site("en.wikipedia.org")
        page = site.pages[title]

        if page.redirect:
            print("🟡 Page is redirect → resolving...")
            page = page.resolve_redirect()

        print("🔵 STEP: Reading raw wiki text")
        raw = page.text()
        print(f"🟠 Raw text length: {len(raw)} chars")

        wikicode = mwparserfromhell.parse(raw)
        sections = wikicode.get_sections(include_lead=True, flat=True)
        print(f"🟡 Found {len(sections)} sections")

        structured = []
        all_images = []
        all_text = []

        img_dir = Path(f"./project/{project_name}/images")
        img_dir.mkdir(parents=True, exist_ok=True)
        print(f"🟡 Image directory: {img_dir}")

        # ---------------------------
        # SECTION LOOP
        # ---------------------------
        for idx, sec in enumerate(sections):
            print(f"\n====================")
            print(f" 🔵 SECTION {idx+1}/{len(sections)}")
            print("====================")

            heading_nodes = sec.filter_headings()
            heading = heading_nodes[0].title.strip() if heading_nodes else "Introduction"
            print(f"🟡 Heading = {heading}")

            raw_text = self.clean_raw_text(sec)
            cleaned = self.deep_clean_text(raw_text)
            wc = len(cleaned.split())
            print(f"🟠 Cleaned word_count = {wc}")

            summary = "" if wc <= 3000 else self.summarize_section(cleaned)

            imgs = self.extract_images(sec)
            print(f"🟠 Found {len(imgs)} wiki image refs")

            sec_imgs = []

            for img in imgs:
                file_name = sanitize_filename(img["file_name"])
                url = self.get_real_url(file_name)
                if not url:
                    print("🔴 Skip (no URL)")
                    continue

                local_path = img_dir / file_name
                self.download_image(url, local_path)

                # ⭐ 自动 SVG → PNG
                final_path = ensure_non_svg(local_path)

                obj = {
                    "file_name": final_path.name,
                    "caption": self.deep_clean_text(img["caption"]),
                    "url": url,
                    "local_path": str(final_path),   # ⭐ 永远是 PNG
                    "section": heading
                }

                sec_imgs.append(obj)
                all_images.append(obj)

            structured.append({
                "heading": heading,
                "summary": summary if summary else cleaned,
                "word_count": wc,
                "images": sec_imgs,
            })

            all_text.append(cleaned)

        output = {
            "clean_text": "\n\n".join(all_text),
            "images": all_images,
            "sections": structured
        }

        print("\n==============================")
        print("   ✅ WikiFetcher RUN DONE")
        print("==============================")
        print(f"⏱ Total time = {time.time() - t0:.2f} sec")
        print(f"🟠 Total sections = {len(structured)}")
        print(f"🟠 Total images   = {len(all_images)}\n")

        return output
