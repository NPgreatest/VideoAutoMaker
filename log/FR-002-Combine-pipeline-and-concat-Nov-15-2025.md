# Feature Request #002: 合并 pipeline.py 和 concat.py

**日期**: 2025-11-15  
**状态**: ✅ 已完成  
**优先级**: 高

---

## 📋 描述

编写一个新的完整的 Python 脚本，支持整个 pipeline 流程。首先使用 pipeline 生成视频片段，完成后使用 `concat.py` 的功能将所有内容合并在一起。用户只需一键即可生成整个视频。

---

## 🎯 目标

创建一个统一的入口点，整合 pipeline 和 concat 功能，提供一键生成完整视频的能力。

---

## 📝 实现要求

1. **不需要重写 concat 和 pipeline 逻辑**
   - 复用 `pipeline.py` 和 `concat.py` 中已有的逻辑
   - 将它们作为 API 函数使用
   - CLI 仅作为入口点

2. **执行流程**
   - 调用 pipeline 生成所有视频片段
   - 验证所有片段生成成功
   - 调用 concat 合并所有片段
   - 返回最终视频

---

## 🔗 相关文件

- `videogen/pipeline/pipeline.py`
- `videogen/pipeline/concat.py`
- `videogen/cli/generate.py`

