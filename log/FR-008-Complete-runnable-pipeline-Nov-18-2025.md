# Feature Request #008: 完整的可运行 Pipeline

**日期**: 2025-11-18  
**状态**: ✅ 已完成  
**优先级**: 高

---

## 📋 描述

完成 `/videogen/cli/generate.py` 中的完整 pipeline，包括生成所有资源、验证结果、重试机制和视频合并。

---

## 🎯 目标

创建一个完整的、可运行的 pipeline，支持：
1. 生成所有资源
2. 验证结果
3. 失败重试
4. 视频合并

---

## 📝 实现要求

### 1. Pipeline 执行流程

```python
def generate_full_video(project_name: str):
    # 1. 调用 pipeline，尝试生成所有资源
    pipeline.run(project_name)
    
    # 2. 验证结果
    if validate_all_results(project_name):
        # 3. 合并视频
        concat_video(project_name)
    else:
        # 2.1 如果某些任务失败，重新运行 pipeline
        retry_pipeline(project_name)
```

### 2. 验证框架

需要验证：
- 每个 block 的 `result.ok` 为 `True`
- `meta.output_path` 存在且文件存在
- `meta.audio_path` 存在且文件存在（如果适用）

### 3. 重试机制

- 每个 block 有重试次数限制
- 在 `.env` 文件中添加 `MAX_RETRY` 配置
- 如果超过最大重试次数，返回错误并停止整个 pipeline
- 在 JSON 文件中标记 pipeline 为失败
- 后续调用 pipeline 时，如果项目已标记为失败，则跳过并返回

### 4. 错误处理

- 记录所有失败的任务
- 提供详细的错误信息
- 支持部分成功的情况

---

## 🔄 执行流程图

```
开始
  ↓
生成所有资源 (pipeline.run)
  ↓
验证结果
  ↓
所有成功? ──否──→ 重试 (最多 MAX_RETRY 次)
  ↓ 是                    ↓
合并视频                 超过重试? ──是──→ 标记失败，停止
  ↓ 否                          ↓
完成                        继续重试
```

---

## 🔗 相关文件

- `videogen/cli/generate.py`
- `videogen/pipeline/pipeline.py`
- `videogen/pipeline/concat.py`
- `videogen/validation/json_validator.py`
- `.env`

