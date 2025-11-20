# Feature Request #001: 重构 worker.py 和 pipeline.py

**日期**: 2025-11-15  
**状态**: ✅ 已完成  
**优先级**: 高

---

## 📋 描述

当前 `pipeline.py` 作为主程序，会向 silicon flow 提交视频生成请求，并调用 `worker.py` 的异步函数等待结果。

现有的 `text_video_silicon` pipeline 有一个 `worker.py`，它是一个后台线程，从 `db/video_download.csv` 轮询结果。

目前这两个任务打包在一个 Python 线程中，需要相互等待，导致混乱。需要拆分为两个线程。

---

## 🎯 目标

### 线程 1: Pipeline 主线程
- 提交视频生成请求
- 如果状态为 `inQueue` 或 `Submitted`，继续处理下一个 block
- 如果返回 `Wrong` 或 `Too many request`，进行重试

### 线程 2: Worker 后台线程
- 定期轮询数据库结果
- 将日志记录到 `./log` 文件夹

### 完成流程
- 整个 pipeline 完成后，设置定时器等待 worker 轮询所有视频下载完成
- 当所有视频都完成后，返回

---

## 📝 实现要求

1. 将 pipeline 主线程和 worker 后台线程分离
2. Pipeline 主线程负责提交任务和重试逻辑
3. Worker 后台线程负责轮询结果和日志记录
4. Pipeline 完成后等待所有 worker 任务完成

---

## 🔗 相关文件

- `videogen/pipeline/pipeline.py`
- `videogen/pipeline/worker.py`
- `db/video_download.csv`

