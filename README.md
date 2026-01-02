# 📚➡️🎬 Wiki2Video
---
![Python](https://img.shields.io/pypi/pyversions/wiki2video)
![PyPI version](https://img.shields.io/pypi/v/wiki2video)
![License](https://img.shields.io/github/license/NPgreatest/wiki2video)

> **From Wikipedia to TikTok/Shorts in One Command.**

Wiki2Video is an AI-powered, fully automated pipeline that turns any Wikipedia article into a narrated, subtitled, cinematic video — ready for YouTube, Shorts, TikTok, or Bilibili.

**No UI.
No timelines.
No manual editing.**

Just one command:

```bash
wiki2video generate https://en.wikipedia.org/wiki/Fermi_paradox
```

Wiki2Video will automatically:

* Fetch the article
* Summarize and rewrite it into a script
* Generate narration (TTS)
* Generate scenes (text-to-video or images)
* Build subtitles
* Render the final mp4


[English](README.md) | [简体中文](README_cn.md)

---

## 🎬 Example Output

| [Oak Island Mystery · Video Mode](https://www.youtube.com/shorts/QA5oeompLAU) | [Fermi Paradox · Image Mode](https://www.youtube.com/shorts/QU2pmhpgsU0) | [Voynich Manuscript · Landscape](https://www.youtube.com/watch?v=0eWaZLgr14M&t=153s) |
|-------------------------------------------------------------------------------|---------------------------------------------------------------------------|-------------------------------------------------------------------------------------|
| <img src="/example/video/example1.gif" width="260">                            | <img src="/example/video/example2.gif" width="260">                       | <img src="/example/video/example3.gif" width="260">                                  |

---

## 🛠️ Installation

The preferred way to install wiki2video is via pip

```bash
pip install wiki2video
```

### OpenAI Backend (Recommended)

Install Wiki2Video with OpenAI support:

```bash
pip install wiki2video[openai]
```

---

## 🚀 Quick Start

Initialize configuration and set your OpenAI API key:

```bash
wiki2video init
```

Generate your first video:

```bash
wiki2video generate <wikipedia_url>
```

---

## 🧪 Try it Live (Google Colab)

Run Wiki2Video end-to-end in your browser — **no local setup required**.


<p>
  <a href="https://colab.research.google.com/drive/1Xwvyk7YJlr6y_Kjr6uN34itBPHB1zAxD?usp=sharing">
    <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/>
  </a>
</p>

**The only thing you need:** an **OpenAI API key**.

This Colab notebook demonstrates:
- Full `wiki2video init`, `wiki2video generate` pipeline
- Script → TTS → Scene generation → Subtitles generation
- Final MP4 rendering


---

## License

MIT License © 2025 NP_123

<p>
  <img src="example/picture/W2V.png" width="80"/>
</p>
