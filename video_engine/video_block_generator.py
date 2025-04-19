import os
import time
import requests

from video_engine import generate_dalle3_image_url
from video_engine.llm_prompt import (
    get_video_query_from_llm,
    get_text_to_image_prompt_from_llm, get_image_to_video_prompt_from_llm
)
from video_engine.pexels_api import get_pexels_video_url
from video_engine.siliconflow_api import (
    generate_siliconflow_video,
    check_siliconflow_video_status, generate_video_from_image_file
)

def generate_video_for_block(block, project_path, index, theme="", regen_image=True, regen_video=True, pre_decision=None):
    from video_engine.llm_prompt import (
        get_text_to_image_prompt_from_llm,
        get_image_to_video_prompt_from_llm
    )

    script = block["text"]
    output_name = os.path.basename(project_path)

    output_image_dir = os.path.join(project_path, "image")
    output_video_dir = os.path.join(project_path, "video")
    os.makedirs(output_image_dir, exist_ok=True)
    os.makedirs(output_video_dir, exist_ok=True)

    image_filename = f"{output_name}_{index + 1}.png"
    video_filename = f"{output_name}_{index + 1}.mp4"

    image_path = os.path.join(output_image_dir, image_filename)
    video_path = os.path.join(output_video_dir, video_filename)

    # Skip if video already exists and not regenerating
    if os.path.exists(video_path) and not regen_video:
        print(f"✅ Video exists, skipping: {video_path}")
        block["video"] = f"video/{video_filename}"
        return

    # Generate prompts (always done fresh)
    print(f"🧠 Generating prompts for block {index + 1}")
    image_prompt = get_text_to_image_prompt_from_llm(script)
    video_prompt = get_image_to_video_prompt_from_llm(script)

    # Generate or reuse image
    if not os.path.exists(image_path) or regen_image:
        print(f"🎨 Generating DALL·E 3 image for: {image_prompt}")
        image_url = generate_dalle3_image_url(image_prompt)

        if not image_url:
            print(f"❌ Failed to get image URL. Skipping block {index + 1}")
            return

        try:
            response = requests.get(image_url)
            response.raise_for_status()
            with open(image_path, "wb") as f:
                f.write(response.content)
            print(f"📥 Image saved to: {image_path}")
        except Exception as e:
            print(f"❌ Failed to download image: {e}")
            return
    else:
        print(f"🖼️ Using cached image: {image_path}")

    # Generate video
    print(f"🎬 Submitting video generation task for: {video_prompt}")
    video_url = generate_video_from_image_file(video_prompt, image_path)

    if video_url:
        try:
            video_data = requests.get(video_url)
            video_data.raise_for_status()
            with open(video_path, "wb") as f:
                f.write(video_data.content)
            print(f"✅ Video saved to: {video_path}")
            block["video"] = f"video/{video_filename}"
        except Exception as e:
            print(f"❌ Failed to download video: {e}")
    else:
        print(f"❌ Video generation failed for block {index + 1}")



def generate_video_for_block_deprecated(block, project_path, index, theme="", reGen=True, pre_decision = None):
    script = block["text"]
    output_name = os.path.basename(project_path)
    output_video = os.path.join(project_path, "video")
    os.makedirs(output_video, exist_ok=True)

    video_filename = f"{output_name}_{index + 1}.mp4"
    video_file_path = os.path.join(output_video, video_filename)

    # 如果视频已存在且不需要重新生成
    if os.path.exists(video_file_path) and not reGen:
        print(f"✅ Video exists, skipping: {video_file_path}")
        block["video"] = f"video/{video_filename}"
        return
    # deprecated method...
    # 决定搜索视频还是生成视频
    decision = pre_decision
    if pre_decision is None or pre_decision!= "search" or pre_decision != "generate":
        print(f"[LLM] Deciding method for: {script}")
        decision = ask_llm_decision(script, theme)
        block["video_generation_method"] = decision

    if decision == "search" or decision: # 短路 省token测试
        query = get_video_query_from_llm(script, theme)
        print(f"[Pexels] Searching video with query: {query}")
        video_url = get_pexels_video_url(query)
        block["video_search_prompt"] = query
        block["video_search_result"] = video_url if video_url else "Not Found"

        if not video_url:
            print(f"❌ No video found for script: {script}")
            block["video"] = "search_failed"
            return

        try:
            print(f"⬇️ Downloading stock video: {video_url}")
            video_response = requests.get(video_url)
            video_response.raise_for_status()
            with open(video_file_path, "wb") as f:
                f.write(video_response.content)
            block["video"] = f"video/{video_filename}"
            print(f"✅ Saved stock video: {video_file_path}")
        except Exception as e:
            print(f"❌ Error downloading video: {e}")
            block["video"] = "download_failed"

    elif decision == "generate":
        print(f"[SiliconFlow] Submitting generation task for: {script}")
        query = get_text_to_image_prompt_from_llm(script)
        print(f"[SiliconFlow] Prompt: {query}")
        request_id = generate_siliconflow_video(query, size="1280x720")

        if not request_id:
            print(f"❌ Failed to get request ID for script: {script}")
            block["video"] = "t2v_failed"
            return

        block["video_generation_request_id"] = request_id
        block["video"] = "t2v_pending"

        # 等待并下载（可选拆分）
        print(f"⏳ Waiting on: {request_id}")
        video_url = None
        for _ in range(60):  # 最多等 10 分钟
            video_url = check_siliconflow_video_status(request_id)
            if video_url:
                break
            time.sleep(10)

        if not video_url:
            print(f"⚠️ Timeout for video: {request_id}")
            block["video"] = "t2v_timeout"
            return

        try:
            print(f"⬇️ Downloading generated video: {video_url}")
            video_response = requests.get(video_url)
            video_response.raise_for_status()
            with open(video_file_path, "wb") as f:
                f.write(video_response.content)
            block["video"] = f"video/{video_filename}"
            print(f"✅ Saved generated video: {video_file_path}")
        except Exception as e:
            print(f"❌ Error saving generated video: {e}")
            block["video"] = "t2v_download_failed"

    else:
        print(f"❓ Unknown decision '{decision}' for: {script}")
        block["video"] = "unknown_decision"
