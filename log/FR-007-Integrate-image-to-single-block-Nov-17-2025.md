# Feature Request #007: 集成图片文件到单个 Block

**日期**: 2025-11-17  
**状态**: ✅ 已完成  
**优先级**: 中

---

## 📋 描述

新的 `remotion` 方法需要将图片文件集成到单个 block 中。图片将保存在项目文件夹中，命名为 `{id}.jpg`。`ScriptBlock` 的 `extra_info` 字段将包含 `single_picture` 字段，值为图片文件名。

---

## 🎯 目标

在 Remotion 视频渲染中支持图片叠加功能，允许将图片文件注入到视频片段中。

---

## 📝 实现要求

### 1. 图片存储

- 图片文件保存在项目文件夹中
- 文件命名格式: `{id}.jpg`
- `ScriptBlock.extra_info` 包含 `single_picture` 字段

### 2. Remotion Method 处理

- `remotion_animation/method.py` 读取图片文件
- 将图片注入到 `remotion_animation/remotion_project/public/assets` 文件夹
- 在视频渲染时使用该图片
- 视频渲染完成后，删除 `public/assets` 中的图片文件

### 3. 数据流

```
项目文件夹/{id}.jpg 
  → remotion_project/public/assets/{id}.jpg 
  → 视频渲染 
  → 删除临时文件
```

---

## 📁 文件结构

```
project/{project_name}/
  ├── {id}.jpg              # 原始图片文件
  └── video/
      └── {target_name}.mp4  # 包含图片的视频

remotion_animation/remotion_project/public/assets/
  └── {id}.jpg              # 临时文件（渲染后删除）
```

---

## 🔗 相关文件

- `videogen/methods/remotion_animation/method.py`
- `videogen/schema/project_schema.py`
- `videogen/methods/remotion_animation/remotion_project/public/assets/`

