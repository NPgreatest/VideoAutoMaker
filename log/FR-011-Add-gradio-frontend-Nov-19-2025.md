# Feature Request #011: 添加 Gradio 前端

**日期**: 2025-11-19  
**状态**: ✅ 已完成  
**优先级**: 高

---

## 📋 描述

使用 Gradio 创建项目前端界面，包含两个子页面：创建项目和生成视频。

---

## 🎯 目标

创建一个用户友好的 Web 界面，支持：
1. 创建新项目
2. 查看项目配置
3. 生成完整视频
4. 实时查看进度

---

## 📝 实现要求

### 1. 子页面 1: 创建项目

**功能:**
- 用户从 `config/character_config.json` 选择角色
- 输入多行格式的脚本（类似 `project_json_generator.py`）
- 点击"创建"按钮创建新项目

**实现:**
- 使用 Gradio 的 `gr.Dropdown` 选择角色
- 使用 `gr.Textbox` 输入脚本（多行）
- 调用项目生成逻辑创建 JSON 文件

### 2. 子页面 2: 生成视频

**功能:**
- 从项目文件夹选择项目
- 显示项目配置（逐行脚本）
- 添加子页面查看原始 JSON
- 点击"生成完整视频"按钮，调用 `cli/generate.py` 开始 pipeline
- 前端持续轮询 JSON 文件，显示每个 block 的进度（Audio, Video, finish 等）

**实现:**
- 使用 `gr.Dropdown` 选择项目
- 使用 `gr.Dataframe` 或 `gr.JSON` 显示配置
- 使用 `gr.Button` 触发生成
- 使用 `gr.Progress` 或自定义组件显示进度
- 使用 JavaScript 或 Python 轮询更新状态

### 3. 进度显示

- 显示每个 block 的状态：
  - Audio: 生成中/完成/失败
  - Video: 生成中/完成/失败
  - Finish: 完成
- 实时更新，无需刷新页面

---

## 🎨 UI 结构

```
Gradio App
├── Tab 1: 创建项目
│   ├── 角色选择器
│   ├── 脚本输入框
│   └── 创建按钮
│
└── Tab 2: 生成视频
    ├── 项目选择器
    ├── 配置显示
    ├── JSON 查看（子页面）
    ├── 生成按钮
    └── 进度显示
```

---

## 🔗 相关文件

- `videogen/gradio_app.py`
- `config/character_config.json`
- `videogen/cli/generate.py`
- `videogen/pipeline/project_json_generator.py`

