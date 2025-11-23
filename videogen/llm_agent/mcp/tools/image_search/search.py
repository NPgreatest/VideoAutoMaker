import requests
from urllib.parse import urlencode

from videogen.core.config_manager import ConfigManager


def google_image_search(query: str) -> list[str]:
    """
    Return list of image URLs from Google Custom Search API.
    Ordered exactly as Google returns.
    """

    api_key = ConfigManager.get("GOOGLE_API_KEY")
    # 支持 GOOGLE_CX_KEY 和 GOOGLE_CX 两种键名
    cx = ConfigManager.get("GOOGLE_CX_KEY")

    if not api_key or not cx:
        # 提供更详细的错误信息，帮助调试
        api_key_status = "已设置" if api_key else "未设置或为空"
        cx_status = "已设置" if cx else "未设置或为空"
        raise RuntimeError(
            f"缺少 Google API 配置。\n"
            f"GOOGLE_API_KEY: {api_key_status}\n"
            f"GOOGLE_CX/GOOGLE_CX_KEY: {cx_status}\n"
            f"请在 Config 页面设置这些值，或确保 .env 文件中包含正确的配置。"
        )

    params = {
        "key": api_key,
        "cx": cx,
        "q": query,
        "searchType": "image",
        "num": 10,
        "safe": "high",
    }

    url = "https://www.googleapis.com/customsearch/v1?" + urlencode(params)
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()

    if "items" not in data:
        return []

    return [item["link"] for item in data["items"] if "link" in item]

