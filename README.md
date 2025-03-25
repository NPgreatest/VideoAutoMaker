# VideoAutoMaker 🎥🤖

VideoAutoMaker is an automated AI-powered video generation pipeline that takes a script and turns it into fully-formed video segments with matching visuals, TTS audio, and metadata — ready for platforms like YouTube, TikTok, and Bilibili.

## ✨ Features

- 🔊 Text-to-Speech: Converts script text into audio using a customizable TTS model (e.g., AI 老高)
- 🎬 Video Clip Search: Automatically queries matching Pexels stock video using an LLM prompt
- 📥 HD Video Download: Pulls and saves the highest-quality mp4 from Pexels
- 🧠 LLM-powered Scene Matching: Uses large language models to generate the most relevant search terms from natural language script
- 📂 Folder-structured Output: Assets saved in organized `audio/` and `video/` folders
- ✅ Ready for post-processing, subtitle alignment, and full video composition

## 📦 Folder Structure

Your project will look like:

```
my_project/ ├── audio/ │ ├── myproj_1.mp3 │ └── myproj_2.mp3 ├── video/ │ ├── myproj_1.mp4 │ └── myproj_2.mp4
```



## 🧩 Requirements

- Python 3.9+
- API Keys:
  - ✅ TTS service URL (custom or commercial)
  - ✅ LLM service (e.g., [siliconflow.cn](https://api.siliconflow.cn))
  - ✅ [Pexels API key](https://www.pexels.com/api/)

## 🚀 How It Works

1. Prepare a `data` dictionary like:

```python
data = {
  "script": [
    {"text": "The universe began with a bang."},
    {"text": "Life formed in oceans billions of years ago."}
  ]
}
```

2. Run the TTS pipeline:

```python
generate_tts_audio(data, project_path="my_project")
```

3. Then run the video generation pipeline:

```python
generate_video_clip(data, project_path="my_project")
```

4. Resulting audio and video clips are saved and linked to `data["script"][i]["audio"]` and `["video"]`

## 🔐 API Configuration

Update your API keys in your Python environment:

```python
PEXELS_API_KEY = "your_pexels_key"
LLM_API_HEADERS = {
  "Authorization": "Bearer your_llm_token",
  "Content-Type": "application/json"
}
```

## 🧠 LLM Prompt Format

The prompt sent to LLM looks like:

> "Given a text script clip, I want to search the corresponding video clip that can match the script, for presentation. Give me the video searching sentence in Pexels API."

## 🗂️ Future Work

- Add subtitle generation (Whisper)
- Add ffmpeg auto video-audio merge
- Add background music / B-roll insertion
- Fully automate YouTube/Bilibili uploads

## 💡 Credits

Built with ❤️ for creative automation.  
Powered by GPT, Pexels, and open tools.

## 📄 License

MIT License.
