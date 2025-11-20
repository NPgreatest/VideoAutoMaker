# 🔥 **FINAL Cursor Prompt（with create_project page, 2025-Nov-20）**

**Task: FR-017 Upgrade Gradio UI + Config Manager + Project Creator (Nov-20-2025)**
Refactor the Gradio UI into a modular multi-page system under `/videogen/ui/`, and implement a dynamic Config Manager + new Project Creator page.
Follow **exactly the steps** below.

---

# ✅ **Step 1 — Split `gradio_app.py` Into 4 Modular UI Pages**

Move all UI logic from the original `gradio_app.py` into:

```
/videogen/ui/
    ├── create_project_page.py
    ├── audio_page.py
    ├── video_page.py
    ├── config_page.py
```

## **1. create_project_page.py（新建）**

用于创建新项目。必须包含：

* 输入框：`project_name`
* 大 textarea：`script_text`
* 按钮：`Create Project`
* Create Project 执行逻辑：

  * 在 `/project/{project_name}/` 创建目录
  * 保存 `raw.json`（保存 script + metadata）
  * 调用 `parse_script_lines` 生成 ScriptBlock[]
  * 使用 WorkingBlockDAO 初始化 `working_blocks.db`
  * 返回成功信息

⚠️ **所有与 project 初始化相关的逻辑必须从 `gradio_app.py` 移出去到这个文件中。**

---

## **2. audio_page.py（原第二页）**

* 一键运行 `run_audio_pipeline(project_name)`
* 刷新频率：**10 秒**
* 每个 WorkingBlock 的 fish_audio 结果用：

```
gr.Audio(value=audio_path)
```

* 支持：

  * 重试该 block
  * 显示 audio duration
  * 显示 character、text

---

## **3. video_page.py（原第三页）**

* 显示最终视频：

```
/project/{project_name}/{project_name}.mp4
```

* 提供“生成视频”按钮，触发 video pipeline
* 提供重试 video block 的功能
* Remotion 或 concat_pipeline 输出路径一律统一

---

## **4. config_page.py（新增配置面板）**

用于加载、修改、保存所有配置参数。
必须展示以下字段，可编辑并保存：

```
SILICONFLOW_API_TOKEN
LLM_DEFAULT_MODEL
AUDIO_FISH_API_KEY

TIKTOK_FORMAT_PICTURE_WIDTH_RATIO
TIKTOK_FORMAT_PICTURE_X_RATIO
TIKTOK_FORMAT_PICTURE_Y_RATIO
TIKTOK_FORMAT_PICTURE_BOTTOM_MARGIN_RATIO

LANDSCAPE_FORMAT_PICTURE_WIDTH_RATIO
LANDSCAPE_FORMAT_PICTURE_X_RATIO
LANDSCAPE_FORMAT_PICTURE_Y_RATIO
LANDSCAPE_FORMAT_PICTURE_BOTTOM_MARGIN_RATIO

FONT_PATH
```

* 页面包含“Load Config”与“Save Config”按钮
* Save 调用 ConfigManager.set()
* 修改后 **立即生效**

---

# ✅ **Step 2 — Implement a Global Config Manager**

Create a new file:

```
/videogen/core/config_manager.py
```

### **Required Features**

#### **1. Load from `.env`**

```python
ConfigManager.get("TIKTOK_FORMAT_PICTURE_WIDTH_RATIO")
```

#### **2. Save back to `.env`**

当用户在 config_page 点击保存：

```python
ConfigManager.set(key, value)
```

* 写回 `.env`
* 刷新内存缓存
* 全局立即生效（Remotion、UI、Pipeline 都能读到新值）

#### **3. Singleton + caching**

避免每次都重新读文件。

#### **4. Default value fallback**

如果 `.env` 里没有，就提供默认值。

---

# ✅ **Step 3 — Update All Remotion Methods to Use ConfigManager**

所有 `/videogen/methods/*` 中与图片位置、宽度、模板参数相关的代码必须改为：

```python
width = ConfigManager.get("TIKTOK_FORMAT_PICTURE_WIDTH_RATIO")
x = ConfigManager.get("TIKTOK_FORMAT_PICTURE_X_RATIO")
y = ConfigManager.get("TIKTOK_FORMAT_PICTURE_Y_RATIO")
...
```

适用于：

* remotion_picture
* remotion_animation
* remotion_video
* 任何用到 TikTok 或 Landscape 模板的地方

⚠️ **禁止硬编码比例值**。

---

# ✅ **Step 4 — Update Main gradio_app.py**

原文件只保留：

```
import gradio as gr
from videogen.ui.create_project_page import build_create_project_page
from videogen.ui.audio_page import build_audio_page
from videogen.ui.video_page import build_video_page
from videogen.ui.config_page import build_config_page
```

并将 4 个页面注册到 Tabs：

```
with gr.Tab("Create Project"):
    build_create_project_page()

with gr.Tab("Audio Pipeline"):
    build_audio_page()

with gr.Tab("Video Pipeline"):
    build_video_page()

with gr.Tab("Config"):
    build_config_page()
```

---

# 🟢 **Deliverables（Cursor 必须创建）**

```
/videogen/ui/create_project_page.py
/videogen/ui/audio_page.py
/videogen/ui/video_page.py
/videogen/ui/config_page.py
/videogen/core/config_manager.py
```

并更新：

* all remotion methods
* project structure
* gradio_app.py
