import os
import requests
from dotenv import load_dotenv

load_dotenv()

LLM_API_TOKEN = os.getenv("LLM_API_TOKEN")
LLM_API_URL = "https://api.siliconflow.cn/v1/chat/completions"
LLM_API_HEADERS = {
    "Authorization": f"Bearer {LLM_API_TOKEN}",
    "Content-Type": "application/json"
}


def ask_llm_decision(script_text, theme):
    prompt = (
        "Given the following script, decide whether we should:\n"
        "- search a video online from a stock video site (output: search)\n"
        "- or generate a video using a text-to-video model (output: generate)\n"
        "Only return 'search' or 'generate', no explanation.\n\n"
        f"Script: {script_text}\n"
        f"Theme: {theme}"
    )
    payload = {
        "model": "deepseek-ai/DeepSeek-V3",
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    try:
        response = requests.post(LLM_API_URL, json=payload, headers=LLM_API_HEADERS)
        response.raise_for_status()
        decision = response.json()["choices"][0]["message"]["content"].strip().lower()
        return "generate" if "generate" in decision else "search"
    except Exception as e:
        print(f"❌ LLM Decision Error: {e}")
        return "search"

def get_video_query_from_llm(script_text, theme):
    prompt = (
        "Given a text script clip, return a short query (within 10 English words) "
        "that can be used to search a relevant video from Pexels.\n"
        "No explanation, just the keywords.\n"
        f"Script:\n{script_text}\n"
        f"Video theme: {theme}\n"
    )
    payload = {
        "model": "deepseek-ai/DeepSeek-V3",
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "max_tokens": 512,
    }
    try:
        response = requests.post(LLM_API_URL, json=payload, headers=LLM_API_HEADERS)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"❌ LLM Prompt Error: {e}")
        return "nature"


def get_text_to_image_prompt_from_llm(scene_describe, chars):
    prompt = (
        "Generate a highly detailed scene description that will be passed to DALLE3, a text-to-image generator. "
        "The description must accurately match the scene provided below.\n\n"
        f"Scene to describe:\n{scene_describe}\n\n"
    )
    if chars: # if select the chars
        prompt += (
            "Additionally, ensure character consistency by replacing any person mentions with the following character descriptions:\n"
            f"{', '.join(f'{name}: {content}' for name, content in chars.items())}\n\n"
        )
    prompt += (
        "Important Instructions:\n"
        "- Output only the final detailed description.\n"
        "- Do not include explanations, headers, or scripts.\n"
        "- Focus on vivid, cinematic, and realistic details."
    )

    payload = {
        "model": "deepseek-ai/DeepSeek-V3",
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "max_tokens": 512,
    }
    try:
        response = requests.post(LLM_API_URL, json=payload, headers=LLM_API_HEADERS)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"❌ LLM Text-to-Image Prompt Error: {e}")
        return "A realistic scene that matches the script content"


def get_image_to_video_prompt_from_llm(script_text):
    pass