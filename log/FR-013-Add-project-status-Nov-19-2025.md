# Feature Request #013: 添加项目状态管理

**日期**: 2025-11-19  
**状态**: ✅ 已完成  
**优先级**: 高

---

## 📋 描述

在 `schema.py` 中添加新的 `ProjectStatus` 枚举，在项目 JSON 中添加新字段。当 pipeline 运行时，设置相应的状态供用户跟踪详细信息。在 Gradio 前端添加进度条显示状态。

---

## 🎯 目标

1. 实现项目状态枚举
2. 在项目 JSON 中存储状态
3. 在 Gradio UI 中显示进度条
4. 移除 `pipeline_failed` 字段，使用状态枚举替代

---

## 📝 实现要求

### 1. ProjectStatus 枚举

在 `schema.py` 中添加：

```python
class ProjectStatus(str, Enum):
    CREATED = "created"           # 项目已创建
    PROCESSING = "processing"      # 正在处理
    RENDERING = "rendering"        # 正在渲染
    FINISHED = "finished"         # 已完成
    FAILED = "failed"             # 失败
```

### 2. 项目 JSON 字段

在项目 JSON 中添加 `status` 字段：
```json
{
  "project_name": "...",
  "status": "processing",
  ...
}
```

### 3. Pipeline 状态更新

- 项目创建时: `status = CREATED`
- Pipeline 开始: `status = PROCESSING`
- 开始渲染: `status = RENDERING`
- 完成: `status = FINISHED`
- 失败: `status = FAILED`

### 4. 失败处理

- 如果重试超过 3 次仍然失败，标记 `ProjectStatus` 为 `FAILED`
- Pipeline 会跳过已标记为 `FAILED` 的项目
- 移除 `pipeline_failed` 字段

### 5. Gradio 进度条

在 Gradio UI 中添加 3 步进度条：
- **步骤 1**: 项目已创建 (CREATED)
- **步骤 2**: 正在处理 (PROCESSING)
- **步骤 3**: 正在渲染 (RENDERING)

**完成状态:**
- 如果完成，标记为绿色或显示"完成"
- 如果失败，显示红色或"失败"

**实现:**
```python
import gradio as gr

def update_progress(status: ProjectStatus):
    steps = ["项目已创建", "正在处理", "正在渲染"]
    current_step = {
        "created": 0,
        "processing": 1,
        "rendering": 2,
        "finished": 3,
        "failed": -1
    }.get(status, 0)
    
    # 更新进度条
    progress.update(value=current_step / 3)
```

---

## 📊 状态流转图

```
CREATED → PROCESSING → RENDERING → FINISHED
                           ↓
                        FAILED
```

---

## 🔗 相关文件

- `videogen/schema/project_schema.py`
- `videogen/pipeline/pipeline.py`
- `videogen/gradio_app.py`

