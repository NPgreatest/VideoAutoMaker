# 📚➡️🎬 **Wiki2Video — Turn Any Wikipedia Page Into a Visual Story**

<p align="center">
  <img src="example/picture/W2V.png" width="180"/>
</p>

> **Every wiki, instantly visualized.**
> Transform long Wikipedia pages into short, cinematic videos — fully automatically.

**Wiki2Video** is an AI-powered pipeline that converts **Wikipedia articles** into **high-engagement short videos** for YouTube, TikTok, Instagram Reels, and educational platforms.
It reads an article, summarizes key sections, generates narration, visuals, subtitles, and produces a polished video — with zero manual editing.

**Input:** a Wikipedia URL
**Output:** a publish-ready short video or long-form explainer

**[中文版本](README_CN.md) | [English](README.md)**

---

# 🎬 Examples (YouTube)

| Type               | Description                                    | Preview                                                                                                                        |
|--------------------| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| 🇺🇸 English Short | **Oak Island Curse — Wiki2Video storytelling** | <a href="https://www.youtube.com/shorts/QA5oeompLAU"><img src="https://img.youtube.com/vi/QA5oeompLAU/0.jpg" width="260"></a>  |
| 🇺🇸 English Short | **Roosevelt & Oak Island — wiki adaptation**   | <a href="https://www.youtube.com/shorts/dA4ruxwJqSw"><img src="https://img.youtube.com/vi/dA4ruxwJqSw/0.jpg" width="260"></a>  |
| 🇺🇸 English Long  | **Full Wiki2Video workflow demo**              | <a href="https://www.youtube.com/watch?v=0eWaZLgr14M"><img src="https://img.youtube.com/vi/0eWaZLgr14M/0.jpg" width="260"></a> |
| 🇨🇳 Chinese Long  | **MH370 storytelling in Laogao style** | <a href="https://youtu.be/MPJBOrTR8v0"><img src="https://img.youtube.com/vi/MPJBOrTR8v0/0.jpg" width="260"></a> |

---

# 🌟 What Is Wiki2Video?

Wiki2Video is a **production-ready AI pipeline** that transforms raw Wikipedia text into a narrative video. It handles:

* Section extraction from Wikipedia
* LLM-powered summarization + restructuring
* Storyboard generation
* Cinematic narration in English or Chinese
* Text-to-video generation
* Auto subtitles + timing alignment
* Background music + mixing
* Final rendering in **both vertical (9:16)** and **horizontal (16:9)** formats

Whether you’re building educational content, history explainers, knowledge channels, or fully automated content studios — Wiki2Video lets you scale instantly.

---

# 🧠 How It Works (High-Level Pipeline)

1. **Fetch Wikipedia article**
   Automatically fetch text, infobox, images, and section structure.

2. **Section-by-section summarization**
   Using LLMs to generate concise, factual summaries.

3. **Story rewriting for video**

   * Punchy
   * Hook-driven
   * 5–8 sec per line
   * Visual-first wording
     Optimized for YouTube/TikTok retention.

4. **Visual generation**

   * AI text-to-video for scenes
   * AI diagram generation when necessary
   * Automatic image selection from Wikimedia

5. **TTS narration**
   Multi-voice
   Emotional control
   Supports long-form videos

6. **Video editing & rendering**

   * Remotion templates
   * Subtitles
   * Music
   * Transitions
   * Final export

---

# 🧩 Features

### ✔ Fully Automated

Just paste a wiki link — everything else is done by the pipeline.


### ✔ Vertical + Horizontal Modes

Produce:

* **YouTube Shorts**
* **TikTok videos**
* **Long-form 16:9 explainers**

### ✔ Regeneratable JSON Pipeline

Modify only the blocks you need.
Everything is stored as editable JSON + assets.

### ✔ Creator + Developer Friendly

You can:

* Run locally
* Extend templates
* Add custom TTS voices
* Add your own video assets
* Run batch jobs

---

# 🖥️ Web UI (Gradio)

<p align="center">
  <img src="example/picture/ui1.png" width="600"/>
</p>

Run the interface:

```bash
python videogen/gradio_app.py
```

Set up environment variables by copying:

```
cp .env_example .env
```

And fill in required API keys.

---

# 🔧 Technologies Behind Wiki2Video

* **LLMs:** DeepSeek-V3 / OpenAI / Qwen
* **Text-to-Video:** Wan2.1 / Wan 2.2 Turbo
* **TTS:** GPT-SoVITS (supports custom voices)
* **Video Rendering:** Remotion (React + FFmpeg)
* **Backend:** Python, SQLite, JSON-structured pipeline
