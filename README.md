# 🎬 VideoGen — AI-Powered Video Generation Pipeline

> *"From words to worlds — VideoGen turns your ideas into living stories."*

**[中文版本](README_CN.md) | [English](README.md)**

VideoGen is an automated AI-powered video generation pipeline that takes a script and turns it into fully-formed video segments with matching visuals, TTS audio, and metadata — ready for platforms like YouTube, TikTok, and Bilibili.

## 🤖 AI Models

- **Text-To-Video Model**: Wan-AI/Wan2.1-T2V-14B-Turbo
- **Audio Model**: GPT-SoVITS (Fine-Tuning)
- **LLM Model**: DeepSeekV3

---

## ⚠️ Development Status

**This project is currently under active development.** The codebase is evolving rapidly, and some features may be unstable or incomplete. 

If you're interested in using VideoGen or contributing to the project, please contact the author directly for the latest information and access.

---

## 🖼️ Web UI Preview

![UI Screenshot](example/picture/ui1.png)

The Gradio-based web interface provides a visual way to browse, edit, and manage your video generation projects.

**How to use:**
```bash
python run_browser.py
```
Then visit `http://localhost:7860` to access the web interface.

---

## 📺 Example Videos

**Example video (Chinese):**

[![Watch the demo video](https://img.youtube.com/vi/RjH_D1CPzps/0.jpg)](https://www.youtube.com/watch?v=RjH_D1CPzps)

**Example video (English):**

![Video_clip](example/picture/video_en.png)

---

## 📄 Project Paper

We've written a paper describing the full pipeline, model integration, and design principles.

[📄 Read the full paper (PDF)](example/paper/paper.pdf)

---

## ✨ Core Features

### 🔊 Text-to-Speech
Converts script into speech using GPT-SoVITS or fine-tuned character voices.

**How to use:** Configure character voices in `config/character_profiles.json`, then the system will automatically generate audio for each script block using the specified character voice.

### 🎬 Visual Matching
LLM-generated search terms fetch relevant video clips from Pexels.

**How to use:** The system automatically analyzes script content and generates search queries. Currently integrated with SiliconFlow video generation API for scene matching.

### 📥 HD Video Download
Auto fetches the best matching stock videos.

**How to use:** Handled automatically by the pipeline when using `text_video` generation method. Videos are downloaded and stored in the project's `video/` directory.

### 🧠 Scene Matching with LLM
Script lines become high-quality video prompts.

**How to use:** The decision system automatically selects the best generation method for each script block. For visual content, LLM generates detailed prompts that are used to create matching video scenes.

### 🎞️ Text-to-Video Generation
Uses models like Wan-AI/Wan2.1-T2V-14B-Turbo for AI-generated visuals.

**How to use:** When the decision system selects `text_video` method, the system automatically submits prompts to the video generation API and manages the asynchronous generation process.

### ✅ JSON + Media Pipeline
Supports block-level audio/video regeneration.

**How to use:** Each project is stored as a JSON file containing all metadata. You can manually edit the JSON to regenerate specific blocks by setting their status to `"pending"` and re-running the pipeline.

### ⚙️ FastAPI-based Control
Full programmatic control via RESTful endpoints (coming soon).

**How to use:** The FastAPI server will provide endpoints for project management, media generation, and pipeline control. This feature is currently under development.

---

## 🛠️ Tech Stack

- **LLM Model**: DeepSeek-V3 (via SiliconFlow API)
- **Text-to-Video Model**: Wan-AI/Wan2.1-T2V-14B-Turbo (via SiliconFlow API)
- **TTS Model**: GPT-SoVITS / FunAudioLLM/CosyVoice2-0.5B (via SiliconFlow API)
- **Animation Engine**: Remotion (React-based video generation)
- **Video Processing**: FFmpeg
- **Web UI**: Gradio
- **Python**: 3.9+

---

## ⚙️ Workflow

### 1. Decision Stage

LLM analyzes each script segment and automatically selects the best generation method:
- `text_video`: Suitable for vivid scenes, actions, or environments
- `remotion_picture`: Suitable for numbers, statistics, comparisons, or structured information
- `subtitle_only`: Suitable for pure narrative text

### 2. Prompt Generation

For blocks requiring visual content, LLM generates detailed video prompts.

### 3. Audio Generation

Uses SiliconFlow TTS API or GPT-SoVITS to generate audio files, supporting:
- Multi-character voices
- Custom character configurations
- Emotion adjustment

### 4. Video Generation

Based on decision results:
- **text_video**: Submit to SiliconFlow video generation API
- **remotion_picture**: Render React animations using Remotion
- **subtitle_only**: Skip video generation

### 5. Video Concatenation

- Audio-video mixing (mux)
- Format normalization (normalize)
- Video concatenation (concat)
- Subtitle generation and beautification
- Subtitle burning (optional)

---

## 📂 Project Configuration

Project JSON file structure:

```json
{
  "project": "my_project",
  "size": "landscape",  // or "tiktok"
  "script": [
    {
      "id": "L1",
      "text": "This is the first script line",
      "voice": "This is the first script line",
      "character": "narrator",
      "decision": "text_video",
      "status": "done",
      "video_generation": {
        "ok": true,
        "artifacts": ["video/L1.mp4"],
        "meta": {
          "video_path": "video/L1.mp4",
          "duration": 5.2
        }
      },
      "audio_generation": {
        "ok": true,
        "artifacts": ["audio/L1.wav"],
        "meta": {
          "audio_path": "audio/L1.wav",
          "total_duration": 5200
        }
      }
    }
  ]
}
```


## 💡 Contributing

**This project is under active development.** If you're interested in using VideoGen or contributing to the project, please contact the author directly.

---


**Built with ❤️ by NP_123**

*Let's turn imagination into moving images.*
