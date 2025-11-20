# Feature Request #003: 重构项目文件夹结构

**日期**: 2025-11-15  
**状态**: ✅ 已完成  
**优先级**: 中

---

## 📋 描述

目前在 `worker.py` 和 `react_render/method.py` 中，所有视频和原始视频都存储在项目文件夹中，扁平化存储在一起。建议创建一个 `video` 文件夹，将所有视频存储在该文件夹中。

---

## 🎯 目标

改善项目文件夹的组织结构，将视频文件统一存储在专门的 `video` 文件夹中，而不是扁平化存储在项目根目录。

---

## 📝 实现要求

1. 在项目文件夹中创建 `video` 子文件夹
2. 修改 `worker.py`，将所有视频输出到 `video` 文件夹
3. 修改 `react_render/method.py`，将所有视频输出到 `video` 文件夹
4. 保持其他文件路径引用的一致性

---

## 📁 新的文件夹结构

```
project/
  {project_name}/
    video/          # 所有视频文件存储在这里
      block_1.mp4
      block_2.mp4
      ...
    {project_name}.json
    ...
```

---

## 🔗 相关文件

- `videogen/pipeline/worker.py`
- `videogen/methods/react_render/method.py`

