# Feature Request #005: 添加 Remotion 方法

**日期**: 2025-11-16  
**状态**: ✅ 已完成  
**优先级**: 高

---

## 📋 描述

将 Remotion 探索项目整合到主项目中，创建一个子模块来生成视频片段。需要编写一个符合主项目 API 的 sub model。

---

## 🎯 目标

创建一个新的 `remotion_animation` 方法，遵循 `BaseMethod` 接口，用于生成基于 Remotion 的视频片段。

---

## 📝 实现要求

### 1. 创建 BaseMethod 实现

需要实现以下接口：

```python
class BaseMethod(abc.ABC):
    NAME: str = "Base"        # Override
    OUTPUT_KIND: str = "any"  # "audio" | "video" | "other"

    @abc.abstractmethod
    def run(self, *, prompt: str, project: str, target_name: str, 
            text: str, workdir: Path, duration_ms: int | None = None, 
            block) -> Dict[str, Any]:
        """Execute the method and return a dict:
        {
          "ok": bool,
          "artifacts": [<paths>],
          "meta": {...},
          "error": <str or None>
        }
        """
        raise NotImplementedError

    def generate_prompt(self, text: str) -> str:
        """Execute the method and return a str: prompt..."""
        raise NotImplementedError
```

### 2. RemotionMethod 实现

- 使用 `@register_method` 装饰器注册方法
- 方法名: `remotion_animation`
- 输出类型: `video`
- 支持从 `block` 参数读取模板信息
- 如果模板匹配，渲染视频；否则抛出异常

### 3. 模板系统

- 当前 Remotion 只有一个模板，但未来可能添加更多
- 模板信息从 `block` 参数中获取
- 需要验证模板是否支持，不支持则抛出异常

### 4. 测试文件

- 在 `remotion_animation` 文件夹中创建 `try_remotion.py`
- 提供使用示例
- 输出到 `./_test_out` 文件夹

---

## 📁 文件结构

```
videogen/methods/remotion_animation/
  ├── method.py          # RemotionMethod 实现
  ├── try_remotion.py    # 测试示例
  └── remotion_project/  # Remotion 项目文件
      └── ...
```

---

## 🔗 相关文件

- `videogen/methods/remotion_animation/method.py`
- `videogen/methods/registry.py`
- `videogen/methods/base_method.py`

