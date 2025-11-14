# 🎬 Video_Auto_Maker — Automated AI Pipeline for Generating Short Videos

> **Give me a piece of text, and I’ll give you a fully produced short video.**  
> *From plain text to TikTok/YouTube-ready videos — fully automated.*

Video_Auto_Maker is an **end-to-end AI-powered video generation system** designed for creators, engineers, and content teams.  
It transforms raw text scripts into fully produced short-form videos, including:

- Scene generation (AI text-to-video / animated diagrams)
- Multi-character TTS narration with emotion control
- Auto-generated & aligned subtitles
- Audio/video stitching, mixing, and timing
- Horizontal & vertical formats for YouTube / TikTok

**Input:** plain text  
**Output:** a publish-ready short video  

**[中文版本](README_CN.md) | [English](README.md)**

---

## 🎬 Input Script vs. Final Generated Videos (Examples)

| 🎞️ Type | 📄 Content Description | 🎥 YouTube Preview (Clickable) |
|:------:|------------------------|:------------------------------:|
| 🇺🇸 English / Vertical | Explaining “Context Window” in LLMs | <a href="https://youtube.com/shorts/Or9nb3m-yKA"><img src="https://img.youtube.com/vi/Or9nb3m-yKA/0.jpg" width="260"></a> |
| 🇨🇳 Chinese / Horizontal | MH370 storytelling in Laogao style | <a href="https://youtu.be/MPJBOrTR8v0"><img src="https://img.youtube.com/vi/MPJBOrTR8v0/0.jpg" width="260"></a> |
| 🇨🇳 Chinese / Vertical | Recreated video in “Hu Chenfeng” opinion style | <a href="https://youtube.com/shorts/dsHxtVA9J6Q"><img src="https://img.youtube.com/vi/dsHxtVA9J6Q/0.jpg" width="260"></a> |

---

## 🎬 Input Script vs. Final Video (Process Demonstration)

**Left: raw text script | Right: fully generated video**

| 📄 Text Script | 🎥 Generated Video |
|----------------|-------------------|
| "dingzhen": Lei, today I found PHP’s Trait…<br>"leijun": Trait is harmless — it’s a safe reuse mechanism in a single-inheritance language…<br>"dingzhen": Feels like magic, like attaching plugins…<br>"leijun": During compilation, Trait code is expanded into the class…<br>[trait_expand.png: Trait expansion diagram]<br>"dingzhen": But not many languages have Traits — outdated?<br>"leijun": No. Traits solve PHP’s reuse pain points, especially for logging, validation, caching…<br>"dingzhen": So it’s for common logic used everywhere?<br>"leijun": Exactly. Traits avoid messy inheritance…<br>[trait_conflict.png: Trait conflict handling]<br> | [![YouTube Video](https://img.youtube.com/vi/f7M_WSHvG8s/0.jpg)](https://youtube.com/shorts/f7M_WSHvG8s) |

---

# 🚀 Project Overview

The goal of Video_Auto_Maker is simple:

> **Convert plain text scripts into fully produced, platform-ready short videos — automatically.**

The pipeline handles *all* steps except writing the script itself:

- AI scene generation (text → video)
- Multi-character and emotional TTS
- Automatic subtitle generation & alignment
- Video/audio stitching, mixing, normalization
- Support for both 16:9 and 9:16 formats
- JSON-driven pipeline & block-level regeneration

Suitable for:

- Technical explainers
- Storytelling shorts
- Narrative vlog-style content
- Documentary narration
- AI avatar / virtual host videos
- Automated content farms & batch production

---

# 🖼️ Web UI (Gradio)

![UI Screenshot](example/picture/ui1.png)

Launch the interface:

```bash
python videogen/gradio_app.py
```

Environment variables:
Copy .env_example → .env and fill in required API keys.

# 🤖 Models Used

Text-to-Video: Wan-AI / Wan2.1-T2V-14B Turbo

Text-to-Speech: GPT-SoVITS (supports custom characters & fine-tuning)

LLM (decision, prompts, storyboarding): DeepSeek-V3

❤️ Author

NP_123
Let's turn imagination into moving images.