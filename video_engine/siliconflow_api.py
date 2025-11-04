import os
import requests
import time
from dotenv import load_dotenv
from video_engine.encode_image import encode_image_to_base64

load_dotenv()

SILICONFLOW_API_TOKEN = os.getenv("SILICONFLOW_API_TOKEN")
SILICONFLOW_SUBMIT_URL = "https://api.siliconflow.cn/v1/video/submit"
SILICONFLOW_STATUS_URL = "https://api.siliconflow.cn/v1/video/status"

HEADERS = {
    "Authorization": f"Bearer {SILICONFLOW_API_TOKEN}",
    "Content-Type": "application/json"
}

# 用于缓存生成请求的 request_id
GENERATED_REQUEST_IDS = []


def check_siliconflow_video_status(request_id):
    try:
        response = requests.post(
            SILICONFLOW_STATUS_URL,
            json={"requestId": request_id},
            headers=HEADERS
        )
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "Succeed":
            video_url = data["results"]["videos"][0]["url"]
            return video_url
        else:
            return None
    except Exception as e:
        print(f"❌ Check Status Error for {request_id}: {e}")
        return None

def generate_video_from_image_file(prompt, image_path, model="Wan-AI/Wan2.1-I2V-14B-720P", size="1280x720", seed=None, negative_prompt=""):
    print(f"📤 Encoding image from: {image_path}")
    image_base64 = encode_image_to_base64(image_path)
    print(f"Encoded imaged base64={image_base64[:10]}, len={(len(image_base64))}")
    if not image_base64:
        print("❌ Could not convert image to base64.")
        return None

    payload = {
        "model": model,
        "prompt": prompt,
        "image_size": size,
        "negative_prompt": negative_prompt,
        "image" : image_base64,
        "seed":seed
    }

    try:
        response = requests.post(SILICONFLOW_SUBMIT_URL, json=payload, headers=HEADERS)
        response.raise_for_status()
        result = response.json()
        request_id = result.get("requestId", None)
        if request_id:
            print(f"Request ID get! id={request_id}")
            GENERATED_REQUEST_IDS.append(request_id)
        return request_id
    except Exception as e:
        print(f"❌ SiliconFlow API Error: {e}")
        return None
