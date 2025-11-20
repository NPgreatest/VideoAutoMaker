# Feature Request #014: 修改 Remotion 方法

**日期**: 2025-11-20  
**状态**: ✅ 已完成  
**优先级**: 中

---

## 📋 描述

修改当前的 `/methods/remotion_animation/method.py`，从 `block.extra_info` 获取图片路径和标题。在 working block 中，如果视频生成结果存在，渲染输出视频，并将信息保存到 `block.remotion_generation`。如果视频生成结果不存在，则保持 working block 为 pending 状态。

---

## 🎯 目标

1. 支持从 `block.extra_info` 读取图片和标题
2. 在视频生成完成后渲染输出视频
3. 将生成信息保存到 block 中
4. 处理视频生成结果不存在的情况

---

## 📝 实现要求

### 1. 数据读取

- 从 `block.extra_info` 读取：
  - `single_picture`: 图片文件路径
  - `title`: 标题文本

### 2. Working Block 处理逻辑

```python
def poll(self, wb: WorkingBlock) -> GenerationResult:
    # 检查视频生成结果是否存在
    if video_generation_result_exists(wb):
        # 渲染输出视频
        output_video = render_video(wb)
        
        # 保存信息到 block.remotion_generation
        save_to_remotion_generation(wb, output_video)
        
        return GenerationResult(ok=True, output_path=output_video)
    else:
        # 保持 pending 状态
        return GenerationResult(ok=False, error="视频生成结果不存在")
```

### 3. TSX 文件修改

需要修改以下文件以支持在视频上渲染图片，而不是黑色背景：
- `FilterTikTokSlide.tsx`
- 其他相关的 TSX 文件

**修改要求:**
- 支持图片叠加在视频上
- 支持标题显示
- 移除黑色背景，使用透明或视频背景

### 4. 数据保存

- 将渲染结果保存到 `block.remotion_generation`
- 包含输出视频路径、元数据等信息

---

## 📊 数据流

```
block.extra_info
  ├── single_picture → 图片路径
  └── title → 标题文本
        ↓
Working Block (检查视频生成结果)
        ↓
存在? ──是──→ 渲染视频 → 保存到 remotion_generation
  ↓ 否
保持 PENDING
```

---

## 🔗 相关文件

- `videogen/methods/remotion_animation/method.py`
- `videogen/methods/remotion_animation/remotion_project/src/FilterTikTokSlide.tsx`
- `videogen/schema/project_schema.py`

