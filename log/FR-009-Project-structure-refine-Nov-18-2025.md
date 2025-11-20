# Feature Request #009: 项目结构优化

**日期**: 2025-11-18  
**状态**: ✅ 已完成  
**优先级**: 中

---

## 📋 描述

当前 `{project_name}_burn.mp4` 和 `{project_name}_final.mp4` 存储在 `_work` 文件夹中，但它们是最终视频。需要将它们重命名为 `{project_name}_nobgm.mp4` 和 `{project_name}.mp4`，存储在项目文件夹的根目录（扁平化），并在 concat 任务完成后删除 `_work` 文件夹。

---

## 🎯 目标

1. 将最终视频文件移到项目根目录
2. 重命名文件以更清晰的命名
3. 清理临时工作文件夹

---

## 📝 实现要求

### 1. 文件重命名和移动

- `{project_name}_burn.mp4` → `{project_name}_nobgm.mp4`
- `{project_name}_final.mp4` → `{project_name}.mp4`
- 从 `_work` 文件夹移动到项目根目录

### 2. 文件夹清理

- Concat 任务完成后，删除 `_work` 文件夹
- 确保所有临时文件都被清理

### 3. 路径更新

- 更新所有引用这些文件路径的代码
- 确保文件移动后所有功能正常工作

---

## 📁 新的文件结构

**之前:**
```
project/{project_name}/
  ├── _work/
  │   ├── {project_name}_burn.mp4
  │   └── {project_name}_final.mp4
  └── {project_name}.json
```

**之后:**
```
project/{project_name}/
  ├── {project_name}_nobgm.mp4  # 无背景音乐版本
  ├── {project_name}.mp4         # 最终版本
  └── {project_name}.json
```

---

## 🔗 相关文件

- `videogen/pipeline/concat.py`
- `videogen/cli/generate.py`

