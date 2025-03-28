import os
import requests
from dotenv import load_dotenv

load_dotenv()

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
LLM_API_TOKEN = os.getenv("LLM_API_TOKEN")

PEXELS_API_URL = "https://api.pexels.com/videos/search?query={query}&per_page=1"
LLM_API_URL = "https://api.siliconflow.cn/v1/chat/completions"
LLM_API_HEADERS = {
    "Authorization": f"Bearer {LLM_API_TOKEN}",
    "Content-Type": "application/json"
}



def get_video_query_from_llm(script_text,theme):
    prompt = (
        "Given a text script clip, I want to search the corresponding video clip "
        "that can match the script, for presentation, give me the video searching sentence in pexels api.\n"
        "directly give me the script english words, within 10 words\n"
        "only output within 10 words, and stop, do not output explanation\n"
        f"Script:\n{script_text}"
        f"The Entire video's title is {theme}"
        f"The keywords do not need to describe the entire script clip, The top priority is to search the top match video clip that can describe the audio."
    )
    payload = {
        "model": "deepseek-ai/DeepSeek-R1 ",
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "max_tokens": 512,
        "temperature": 0.7,
        "top_p": 0.7,
        "top_k": 50,
        "frequency_penalty": 0.5,
        "n": 1,
        "response_format": {"type": "text"},
    }
    try:
        response = requests.post(LLM_API_URL, json=payload, headers=LLM_API_HEADERS)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"❌ LLM API Error: {e}")
        return "nature"  # fallback


def get_pexels_video_url(query):
    headers = {"Authorization": PEXELS_API_KEY}
    url = PEXELS_API_URL.format(query=query)
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        video_data = response.json()
        video_files = []

        for video in video_data.get("videos", []):
            if video["width"] > video["height"]:  # landscape check
                video_files.extend(video["video_files"])

        if not video_files:
            print("❌ No landscape video files found.")
            return None

        # Pick the highest resolution landscape video
        best_video_file = sorted(video_files, key=lambda x: x["width"], reverse=True)[0]
        return best_video_file["link"]
    except Exception as e:
        print(f"❌ Pexels API Error: {e}")
        return None



def generate_video_clip(data, project_path, reGen=True, theme = ""):
    output_name = os.path.basename(project_path)
    output_video = os.path.join(project_path, "video")
    os.makedirs(output_video, exist_ok=True)

    for index, block in enumerate(data["script"]):
        script = block["text"]
        video_filename = f"{output_name}_{index + 1}.mp4"
        video_file_path = os.path.join(output_video, video_filename)

        if os.path.exists(video_file_path) and not reGen:
            print(f"Video exists, skipping: {video_file_path}")
            data["script"][index]["video"] = f"video/{video_filename}"
            continue

        print(f"[LLM] Getting query for script: {script}")
        query = get_video_query_from_llm(script,theme)
        print(f"[Pexels] Searching video with query: {query}")
        video_url = get_pexels_video_url(query)

        if not video_url:
            print(f"❌ No video found for script: {script}")
            continue

        try:
            print(f"⬇️ Downloading video: {video_url}")
            video_response = requests.get(video_url)
            video_response.raise_for_status()
            with open(video_file_path, "wb") as f:
                f.write(video_response.content)
            data["script"][index]["video"] = f"video/{video_filename}"
            print(f"✅ Saved video: {video_file_path}")
        except Exception as e:
            print(f"❌ Error downloading video: {e}")
            continue

    return data
