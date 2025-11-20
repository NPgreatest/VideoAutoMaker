# Feature Request #010: 自定义角色

**日期**: 2025-11-18  
**状态**: ✅ 已完成  
**优先级**: 中

---

## 📋 描述

当前 `AUDIO_FISH_MODEL_ID` 和 `PICTURE_PATH` 从 `.env` 文件中读取。希望从项目 JSON 的 block `character` 字段读取这些信息，从 `character_config.json` 获取配置。在合并视频时，`add_picture.py` 过程也应该从 block 的 `character` 字段读取图片地址。

---

## 🎯 目标

1. 支持每个 block 使用不同的角色配置
2. 从 `character_config.json` 读取角色信息
3. 移除对 `.env` 中角色配置的依赖

---

## 📝 实现要求

### 1. 角色配置读取

- 从项目 JSON 的 `block.character` 字段读取角色名称
- 从 `config/character_config.json` 读取角色详细信息
- 配置包含：
  - `AUDIO_FISH_MODEL_ID`
  - `PICTURE_PATH`
  - 其他角色相关配置

### 2. Audio Fish 方法

- 修改 `audio_fish/method.py`
- 从 block 的 `character` 字段获取 `AUDIO_FISH_MODEL_ID`
- 不再从 `.env` 读取

### 3. Add Picture 过程

- 修改 `add_picture.py`
- 从 block 的 `character` 字段读取图片地址
- 支持每个 block 使用不同的角色图片

### 4. 配置结构

`character_config.json` 示例：
```json
{
  "character_name": {
    "audio_model_id": "...",
    "picture_path": "...",
    ...
  }
}
```

---

## 📊 数据流

```
项目 JSON (block.character)
  ↓
character_config.json (查找配置)
  ↓
Audio Fish / Add Picture (使用配置)
```

---

## 🔗 相关文件

- `config/character_config.json`
- `videogen/methods/audio_fish/method.py`
- `videogen/pipeline/add_picture.py`
- `videogen/schema/project_schema.py`

