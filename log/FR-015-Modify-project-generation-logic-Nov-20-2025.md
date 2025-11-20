# Feature Request #015: 修改项目生成逻辑

**日期**: 2025-11-20  
**状态**: ✅ 已完成  
**优先级**: 中

---

## 📋 描述

在 `gradio_app.py` 中，当用户点击"创建项目"按钮时，需要将生成过程抽象到 `pipeline` 文件夹中的一个文件，并添加一些新规则。

---

## 🎯 目标

1. 将项目生成逻辑从 Gradio 中分离
2. 支持特定角色配置
3. 支持图片 block 识别

---

## 📝 实现要求

### 1. 抽象生成逻辑

- 在 `pipeline` 文件夹中创建新文件（如 `project_generator.py`）
- 将项目生成逻辑从 `gradio_app.py` 移到此文件
- `gradio_app.py` 只负责调用生成函数

### 2. 特定角色规则

如果行以 `"character_name": xxxx` 开头，则：
- 该行之后的 block 使用指定的角色
- 直到遇到下一个 `character_name` 或文件结束

**示例:**
```
character_name: 丁真
这是第一段文本
这是第二段文本
character_name: 雷军
这是第三段文本
```

### 3. 图片 Block 识别

如果整行是 `[Lx.png:picture title...]` 格式，则：
- 将其视为前一个 block 的图片 block
- 在 `extra_info` 字段中添加：
  - `title`: 图片标题
  - `template`: `FilterTikTokSlide`
  - `single_picture`: 图片文件名（`Lx.png`）

**示例:**
```
这是文本内容
[L1.png:这是图片标题]
```

**生成的 JSON:**
```json
{
  "blocks": [
    {
      "text": "这是文本内容",
      "extra_info": {
        "title": "这是图片标题",
        "template": "FilterTikTokSlide",
        "single_picture": "L1.png"
      }
    }
  ]
}
```

### 4. 文件结构

```
videogen/pipeline/
  ├── project_generator.py  # 新增：项目生成逻辑
  └── ...

videogen/gradio_app.py      # 修改：调用 project_generator
```

---

## 📋 解析规则总结

1. **角色指定**: `character_name: <name>`
2. **图片 Block**: `[<filename>:<title>]`
3. **普通文本**: 其他所有行

---

## 🔗 相关文件

- `videogen/gradio_app.py`
- `videogen/pipeline/project_generator.py` (新建)
- `videogen/schema/project_schema.py`

