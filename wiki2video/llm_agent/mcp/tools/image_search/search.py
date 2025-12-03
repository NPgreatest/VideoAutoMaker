import requests
from urllib.parse import urlencode

from wiki2video.config.config_manager import config


def google_image_search(query: str) -> list[str]:
    """
    Return list of image URLs from Google Custom Search API.
    Ordered exactly as Google returns.
    """

    api_key = config.get("api_keys", "google_api_key")
    cx = config.get("api_keys", "google_cx_key")

    if not api_key or not cx:
        api_key_status = "已设置" if api_key else "未设置或为空"
        cx_status = "已设置" if cx else "未设置或为空"
        raise RuntimeError(
            f"缺少 Google API 配置。\n"
            f"GOOGLE_API_KEY: {api_key_status}\n"
            f"GOOGLE_CX_KEY: {cx_status}\n"
            f"请在 Config 页面设置这些值。"
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
