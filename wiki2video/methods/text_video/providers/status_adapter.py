# text_video/providers/status_adapter.py

def normalize_status(platform: str, raw_status: str) -> str:
    """
    将不同平台的 raw 状态转成标准状态：
    - success
    - wait
    - error
    """
    s = raw_status.strip()

    if platform == "siliconflow":
        if s == "Succeed":
            return "success"
        if s == "Failed":
            return "error"
        return "wait"

    if platform == "openai":
        print(f"[text_video] s={s}")
        if s == "completed":
            return "success"
        if s == "failed":
            return "error"
        return "wait"

    if platform == "google":
        print(f"[text_video] s={s}")
        if s == "success":
            return "success"
        if s == "error":
            return "error"
        return "wait"


    # fallback
    print("[text_video] ERROR, Unknown platform")
    return "error"
