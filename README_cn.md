# 📚➡️🎬 Wiki2Video

> **一行命令，将任意维基百科页面自动生成视频。**

Wiki2Video 是一个 **AI 驱动的全自动视频生成流水线**，可将任意 Wikipedia 文章转换为 **带配音、字幕和视觉内容的成片视频**，适用于：

- YouTube
- Shorts / TikTok
- Bilibili

无需界面操作，无需时间线剪辑。

**没有 UI  
没有时间轴  
没有手动编辑**

只需一行命令：

```bash
wiki2video generate https://en.wikipedia.org/wiki/Rongorongo
```

[English](README.md) | [简体中文](README_cn.md)

---

## 🧠 工作流程

Wiki2Video 会自动完成以下步骤：

1. 获取并解析 Wikipedia 页面
2. 总结并改写为解说脚本
3. 生成配音（TTS）
4. 生成画面（文生视频 / 文生图片）
5. 生成字幕
6. 渲染最终 mp4 视频

整个流程 **完全自动化**，可复现、可批量。

---

## 🎬 示例效果

| Oak Island Mystery · 视频模式                           | Fermi Paradox · 图片模式                                | Voynich Manuscript · 横屏                             |
| --------------------------------------------------- | --------------------------------------------------- | --------------------------------------------------- |
| <img src="/example/video/example1.gif" width="260"> | <img src="/example/video/example2.gif" width="260"> | <img src="/example/video/example3.gif" width="260"> |

> 点击标题可跳转至对应的 YouTube 完整视频。

---

## 🛠️ 安装


```bash
pip install wiki2video
```

### 使用 OpenAI 后端（推荐）

```bash
pip install wiki2video[openai]
```

---

## 🚀 快速开始

初始化配置并设置 OpenAI API Key：

```bash
wiki2video init
```

生成你的第一个视频：

```bash
wiki2video generate <wikipedia_url>
```

## 🧪 在线尝试 (Google Colab)

在浏览器里使用 Wiki2Video — **不需要安装任何本地依赖**.


<p>
  <a href="https://colab.research.google.com/drive/1Xwvyk7YJlr6y_Kjr6uN34itBPHB1zAxD?usp=sharing">
    <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/>
  </a>
</p>

**您只需要:** 一个 **OpenAI API key**.

这个 Colab notebook 展示了:
- 完整的 `wiki2video init `, `wiki2video generate` 流水线
- 剧本 → TTS → 生成画面 → 生成字幕
- 最后 MP4 渲染


---

## 📄 许可证

MIT License © 2025 NPgreatest

