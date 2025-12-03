# 📚➡️🎬 **Wiki2Video — Turn Any Wikipedia Page Into a Video**

<p align="center">
  <img src="example/picture/W2V.png" width="180"/>
</p>

> **Convert any Wikipedia page into a fully edited video — instantly, with a single CLI command.**

Wiki2Video is an AI-powered pipeline that transforms **Wikipedia articles** into **high-engagement short videos** with narration, AI-generated visuals, subtitles, and cinematic editing.

No UI, no timeline dragging — just:

```bash
wiki2video generate https://en.wikipedia.org/wiki/Rongorongo
```

Wiki2Video will automatically:

* Fetch the article
* Summarize and rewrite it into a script
* Generate narration (TTS)
* Generate scenes (text-to-video or images)
* Build subtitles
* Render the final mp4

A complete video pipeline, entirely automated.

---

# 🎬 Example Output (YouTube)

| Type               | Description                                 | Preview                                                                                                                        |
| ------------------ | ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| 🇺🇸 English Short | Oak Island Mystery — TikTok/Shorts          | <a href="https://www.youtube.com/shorts/QA5oeompLAU"><img src="https://img.youtube.com/vi/QA5oeompLAU/0.jpg" width="260"></a>  |
| 🇺🇸 English Long  | Voynich Manuscript — YouTube Explainer      | <a href="https://www.youtube.com/watch?v=0eWaZLgr14M"><img src="https://img.youtube.com/vi/0eWaZLgr14M/0.jpg" width="260"></a> |
| 🇨🇳 Chinese Story | MH370 Explained — Laogao-style storytelling | <a href="https://youtu.be/MPJBOrTR8v0"><img src="https://img.youtube.com/vi/MPJBOrTR8v0/0.jpg" width="260"></a>                |

---

# ⚡ Key Features

### ✅ **Lightning-Fast CLI Workflow**

**Designed for creators and automation pipelines — everything works headless, scriptable, and batch-friendly.**
You can generate 1 or 100 videos with the same CLI.

### ✅ **Regeneratable, Editable JSON Pipeline**

Each project is stored as:

* script blocks
* narration text
* video prompts
* assets
* timing

Modify only what you want. Re-render anytime.

### ✅ **Vertical + Horizontal Output**

Produce:

* **9:16 TikTok / Shorts**
* **16:9 YouTube explainers**

### ✅ **Professional Rendering (MoviePy + FFmpeg)**

Under the hood:

* transitions
* overlays
* subtitles
* effects
* BGM mixing

Fully open-source, fully customizable.

### ✅ **Flexible AI Provider System**

Mix and match AI engines you prefer:

* **LLM:** OpenAI / Google / SiliconFlow
* **TTS:** OpenAI / Fish Audio
* **Text-to-Video:** OpenAI Sora API / SiliconFlow
* **Images:** OpenAI / SiliconFlow

Configure everything via CLI:

```bash
wiki2video config --set platforms.llm=openai
wiki2video config --set api_keys.openai_api_key=sk-xxx
```

---

# 🛠️ Installation

### 📦 Coming soon to PyPI

This project will be published to PyPI soon.
Once available, you will be able to install it directly via:

```bash
pip install wiki2video
```

Until then, please install from source:

```bash
git clone https://github.com/NPgreatest/Wiki2Video.git
cd wiki2video
pip install -e .
```

Check environment:

```bash
wiki2video doctor
```

---

# 🧠 Full CLI Overview

Available commands:

```
wiki2video generate <wiki-url>     # Convert a Wikipedia page into a full project + video
wiki2video script <wiki-url>       # Generate only a script/story (no video)
wiki2video render <project_name>   # Render an existing project folder
wiki2video config --show           # View config.json
wiki2video config --set ...        # Update config.json
wiki2video doctor                  # Environment diagnostics
wiki2video cost                    # Estimate API cost
wiki2video init                    # Create an empty project template
```

Powered by **Typer** — includes autocomplete, help menus, and colorized output.

---

# 🎛️ Configuration (config.json)

Config file lives at:

```
~/.config/wiki2video/config.json
```

It is generated automatically on first run.

---

# 🖥️ Web UI (Optional)

If you prefer a graphical interface:

```bash
python wiki2video/gradio_app.py
```

<p align="center">
  <img src="example/picture/ui1.png" width="600"/>
</p>

---

# ⭐ Why Wiki2Video Is Unique

🔥 **The first fully-automated “Wikipedia → Video” CLI pipeline on GitHub.**
While most tools rely on heavy UI timelines, Wiki2Video is:

* headless
* programmable
* automation-friendly
* suitable for batch video generation
* ideal for content studios and educational channels

Perfect for:

* automated YouTube channels
* TikTok/Shorts production
* research/education content
* narrative explainers
* batch processing systems
* AI-driven content studios

---

# 🎉 Try It Now

```bash
wiki2video generate https://en.wikipedia.org/wiki/Rongorongo
```

Sit back — the AI will write, narrate, visualize, subtitle, and render the whole video for you.
