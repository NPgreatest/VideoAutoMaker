# 📚➡️🎬 **Wiki2Video — 让任何一篇 Wikipedia 文章变成可视化故事**

<p align="center">
  <img src="example/picture/W2V.png" width="180"/>
</p>

> **让所有维基知识立即可视化。**
> 一键把长篇维基百科内容变成短小精悍、有画面感的视频。

**Wiki2Video** 是一个 AI 驱动的自动化视频生成流水线，它能把 **Wikipedia 文章** 转换成 **高吸引力的短视频或长视频**（YouTube、TikTok、小红书、Bilibili 都可直接发布）。

它会自动读取 Wiki 文章 → 总结内容 → 转换成可视化叙事 → 生成配音 → 生成画面 → 输出成完整成片，无需任何手动剪辑。

**输入：** 一条 Wikipedia 链接
**输出：** 可直接发布的短视频或长视频

---

# 🎬 示例（YouTube）

| 类型                 | 内容简介                                        | 预览                                                                                                                                         |
| -------------------- | ------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------- |
| 🇺🇸 英文 / 短视频 | **橡树岛诅咒 — Wiki2Video 故事化演绎**       | <a href="https://www.youtube.com/shorts/QA5oeompLAU"><img src="https://img.youtube.com/vi/QA5oeompLAU/0.jpg" width="260"></a>               |
| 🇺🇸 英文 / 短视频 | **罗斯福与橡树岛 —— 基于 Wiki 的历史改写** | <a href="https://www.youtube.com/shorts/dA4ruxwJqSw"><img src="https://img.youtube.com/vi/dA4ruxwJqSw/0.jpg" width="260"></a>               |
| 🇺🇸 英文 / 长视频 | **完整 Wiki2Video 工作流演示**               | <a href="https://www.youtube.com/watch?v=0eWaZLgr14M"><img src="https://img.youtube.com/vi/0eWaZLgr14M/0.jpg" width="260"></a>               |
| 🇨🇳 中文 / 长视频  | **MH370 老高风格叙事视频**                    | <a href="https://youtu.be/MPJBOrTR8v0"><img src="https://img.youtube.com/vi/MPJBOrTR8v0/0.jpg" width="260"></a>                              |

---

# 🌟 Wiki2Video 是什么？

Wiki2Video 是一个 **可投入生产的自动化 AI 视频制作系统**，可以将一整篇 Wikipedia 文章处理成可直接发布的叙事视频。它包括：

* 自动解析 Wiki 各章节内容
* 使用大模型进行总结与结构化重写
* 自动生成故事式分镜（storyboard）
* 英文 / 中文两种叙事风格
* AI 文本生成视频（text-to-video）
* 自动生成字幕、时间轴、音画同步
* 自动加背景音乐、音量处理
* 输出 **竖屏（9:16）** 与 **横屏（16:9）** 完整成片

无论你是在做知识类频道、历史解说、教育内容、或想做自动化内容产线，Wiki2Video 都能实现一键规模化。

---

# 🧠 工作流程（高层架构）

1. **读取 Wikipedia 文章**
   自动抓取正文、信息框、图片、章节结构。

2. **逐章节总结内容**
   使用 LLM 生成精准、简洁、不臆测的内容摘要。

3. **重写成视频脚本**

   * 开头有强 Hook
   * 每行 5–8 秒
   * 更具画面感
   * 更适合 TikTok/YouTube 的叙事节奏

4. **生成画面（Visual Generation）**

   * AI 文生视频
   * 自动生成示意图
   * 从 Wikimedia 自动抽取图片素材

5. **多角色配音（TTS）**

   * 可选多种音色
   * 情绪控制
   * 支持长视频连续讲话

6. **自动剪辑与渲染**

   * 基于 MoviePy 的模板体系
   * 字幕、背景音乐、转场、节奏全自动
   * 多格式统一导出

---

# 🧩 项目特色

### ✔ 完全自动化

只需贴上 Wiki 链接，所有后续工作系统自动完成。

### ✔ 支持横竖屏双格式

输出适用于：

* **YouTube Shorts / TikTok / Reels**
* **横屏 16:9 解释类长视频**

### ✔ JSON 可再生成流水线

任意一段不满意都能单独重新生成，无需重做整部视频。

### ✔ 面向创作者 & 工程师

你可以：

* 本地运行
* 自定义模板
* 加自己的声音
* 加自己的视频素材
* 批量生成视频

---

# 🖥️ Web UI（Gradio）

<p align="center">
  <img src="example/picture/ui1.png" width="600"/>
</p>

启动界面：

```bash
python videogen/gradio_app.py
```

配置环境变量：

```
cp .env_example .env
```

并填入所需 API Key。

---

# 🔧 技术栈

* **大模型（LLM）：** DeepSeek-V3 / OpenAI / Qwen
* **文本转视频（T2V）：** Wan2.1 / Wan 2.2 Turbo
* **文本转语音（TTS）：** GPT-SoVITS（支持自定义角色）
* **视频渲染：** MoviePy（Python + FFmpeg）
* **后端：** Python、SQLite、JSON 可编辑流水线
