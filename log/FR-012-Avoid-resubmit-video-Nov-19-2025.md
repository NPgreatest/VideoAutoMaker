# Feature Request #012: 避免重新提交视频

**日期**: 2025-11-19  
**状态**: ✅ 已完成  
**优先级**: 中

---

## 📋 描述

防止用户重复提交视频生成请求，避免重复任务和资源浪费。

---

## 🎯 目标

1. 在 pipeline 运行前检查是否有待处理的任务
2. 在 pipeline 运行时禁用"开始制作"按钮
3. 防止用户多次点击导致重复提交

---

## 📝 实现要求

### 1. Pipeline 检查

在 `pipeline.py` 中：
- 检查数据库，查看是否有任何当前待处理的任务
- 如果有待处理任务，先调用 worker 完成当前任务
- 然后再运行新的 pipeline

**实现逻辑:**
```python
def run_pipeline(project_name: str):
    # 检查是否有待处理任务
    pending_tasks = dao.get_pending(project_name)
    if pending_tasks:
        # 先完成当前任务
        worker.run_until_complete(project_name)
    
    # 然后运行新的 pipeline
    pipeline.build_and_run(project_name)
```

### 2. Gradio UI 状态管理

在 `gradio_app.py` 中：
- 当 pipeline 正在运行时，设置"开始制作"按钮为 `processing` 状态
- 禁用按钮，防止用户点击两次
- Pipeline 完成后，恢复按钮状态

**实现:**
```python
def generate_video(project_name: str):
    # 设置按钮为 processing
    button.update(value="处理中...", interactive=False)
    
    try:
        # 运行 pipeline
        result = generate_full_video(project_name)
    finally:
        # 恢复按钮状态
        button.update(value="开始制作", interactive=True)
```

---

## 🔄 执行流程

```
用户点击"开始制作"
  ↓
检查是否有待处理任务
  ↓
有? ──是──→ 完成当前任务
  ↓ 否
运行新 pipeline
  ↓
按钮状态: processing (禁用)
  ↓
Pipeline 完成
  ↓
按钮状态: 正常 (启用)
```

---

## 🔗 相关文件

- `videogen/pipeline/pipeline.py`
- `videogen/gradio_app.py`
- `videogen/dao/working_block_dao.py`

