import os
from dotenv import load_dotenv
from openai import OpenAI

# Load .env file to get the OpenAI API key
load_dotenv()
silicon_flow_api = os.getenv("SILICONFLOW_API_TOKEN")


import requests

url = "https://api.siliconflow.cn/v1/images/generations"

def generate_silicon_flow_image_url(prompt: str) -> str:
    try:

        payload = {
            "model": "Kwai-Kolors/Kolors",
            "prompt": f"Generate Ghibli style image: {prompt}",
            "image_size": "2048x1152",
            "batch_size": 1,
            "num_inference_steps": 20,
            "guidance_scale": 7.5
        }
        headers = {
            "Authorization": f"Bearer {silicon_flow_api}",
            "Content-Type": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers)
        resp = response.json()
        image_url = resp["images"][0]["url"]
        return image_url
    except Exception as e:
        print(f"❌ Silicon Flow Image API Error: {e}")
        return None


# Example usage
if __name__ == "__main__":
    test_prompt = (
        "Shi Qiang casually leaning against the wall, deeply inhaling his cigarette smoke, expression rude and impatient, the narrow corridor lit by dim fluorescent lights, smoke filling the air around him."
    )
    image_url = generate_silicon_flow_image_url(test_prompt)
    if image_url:
        print(f"✅ Image URL: {image_url}")
    else:
        print("❌ Failed to generate image.")
