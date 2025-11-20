# Feature Request #004: 适配横屏和竖屏视频格式

**日期**: 2025-11-16  
**状态**: ✅ 已完成  
**优先级**: 高

---

## 📋 描述

当前项目仅支持 1280x720 格式的视频。需要添加一个新参数 `size` 到 JSON 配置文件中，用户可以选择横屏（landscape）和 TikTok 格式（9:16 竖屏）。

---

## 🎯 目标

支持两种视频格式：
- **横屏 (landscape)**: 1280x720
- **竖屏 (tiktok)**: 720x1280

---

## 📝 实现要求

### 1. JSON 配置文件
- 在生成 JSON 文件时添加 `size` 选项
- 支持两种格式：`"landscape"` 和 `"tiktok"`

### 2. React Render 方法
- 修改 `methods.react_render`，支持 TikTok 格式录制
- 根据配置选择正确的视频尺寸

### 3. Silicon Flow 生成格式
- 修改对应的 silicon flow 生成格式为 `1280x720` 或 `720x1280`
- 根据项目配置传递正确的尺寸参数

### 4. Concat 功能
- 修改 `concat.py`，支持 TikTok 格式的视频合并
- 确保合并后的视频保持正确的宽高比

---

## 📐 视频格式规格

| 格式 | 宽度 | 高度 | 宽高比 |
|------|------|------|--------|
| landscape | 1280 | 720 | 16:9 |
| tiktok | 720 | 1280 | 9:16 |

---

## 🔗 相关文件

- `videogen/pipeline/project_json_generator.py`
- `videogen/methods/react_render/method.py`
- `videogen/pipeline/concat.py`
- `videogen/schema/project_schema.py`

