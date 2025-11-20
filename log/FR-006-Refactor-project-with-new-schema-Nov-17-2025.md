# Feature Request #006: 基于新 Schema 重构项目

**日期**: 2025-11-17  
**状态**: ✅ 已完成  
**优先级**: 高

---

## 📋 描述

重构了 `schema.py`，更新了一些字段。`WorkingBlock` 将存储在 SQLite 中，而不是使用 `db/video_download.csv`。需要创建一个 SQLite 文件，并将 working block 存储在其中。

---

## 🎯 目标

1. 将 `WorkingBlock` 存储从 CSV 迁移到 SQLite
2. 重构 `worker.py`，将 worker 抽象为全局功能
3. `remotion` 和 `text_video_silicon` 使用同一个全局 worker
4. `method->run` 函数只创建 `WorkingBlock` 并推送到 SQLite
5. Pipeline 结束时启动 worker 并等待结果

---

## 📝 实现要求

### 1. SQLite 数据库

- 创建 SQLite 数据库文件（替代 `db/video_download.csv`）
- 设计 `working_blocks` 表结构
- 实现数据库初始化脚本

### 2. Worker 重构

- 将 worker 抽象为全局功能
- 所有方法共享同一个 worker 实例
- Worker 从 SQLite 读取待处理任务
- Worker 轮询并更新任务状态

### 3. Method 接口调整

- `method->run` 函数只负责创建 `WorkingBlock`
- 将 `WorkingBlock` 保存到 SQLite
- 不执行实际的重型工作

### 4. Pipeline 流程

- Pipeline 构建所有 `WorkingBlock` 并保存到 SQLite
- Pipeline 结束时启动全局 worker
- Worker 处理所有待处理任务
- Pipeline 等待所有任务完成

---

## 📊 数据库 Schema

```sql
CREATE TABLE working_blocks (
    id TEXT PRIMARY KEY,
    project_name TEXT NOT NULL,
    block_id TEXT NOT NULL,
    method_name TEXT NOT NULL,
    status TEXT NOT NULL,
    config_json TEXT,
    result_json TEXT,
    output_path TEXT,
    prev_ids TEXT,  -- JSON array
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🔗 相关文件

- `videogen/schema/working_block.py`
- `videogen/dao/working_block_dao.py`
- `videogen/pipeline/worker.py`
- `videogen/pipeline/pipeline.py`
- `setup_database.py`

