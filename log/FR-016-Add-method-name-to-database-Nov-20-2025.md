# Feature Request #016: 在 working_blocks.db 中添加 method_name

**日期**: 2025-11-20  
**状态**: ✅ 已完成  
**优先级**: 高

---

## 📋 描述

我们可能需要在同一个 block 中执行多个任务，因此需要在 `working_blocks.db` 中添加 `method_name` 字段，以便知道使用哪个方法。

---

## 🎯 目标

1. 在数据库 schema 中添加 `method_name` 字段
2. 在创建和读取 working block 时处理 `method_name`
3. 根据 `method_name` 创建相应的方法实例

---

## 📝 实现要求

### 1. 数据库 Schema 更新

在 `setup_database.py` 中：
- 添加 `method_name` 字段到 `working_blocks` 表
- 字段类型: `TEXT`
- 字段约束: `NOT NULL`

**SQL 更新:**
```sql
ALTER TABLE working_blocks 
ADD COLUMN method_name TEXT NOT NULL DEFAULT '';
```

### 2. WorkingBlockDAO 更新

在 `working_block_dao.py` 中：
- 更新 `create` 方法，保存 `method_name`
- 更新 `get` 和 `get_all` 方法，读取 `method_name`
- 确保所有数据库操作都包含 `method_name`

### 3. Global Worker 更新

在 `global_worker.py` 中：
- 创建 working block 时，添加 `method_name` 字段
- 读取 working block 时，获取 `method_name`
- 根据 `method_name` 从 `MethodRegistry` 创建相应的方法实例

**实现逻辑:**
```python
def process_working_block(wb: WorkingBlock):
    # 根据 method_name 获取方法
    method = MethodRegistry.get_method(wb.method_name)
    
    # 调用方法的 poll 函数
    result = method.poll(wb)
    
    # 更新 working block
    update_working_block(wb, result)
```

### 4. Method 创建逻辑

确保 `MethodRegistry` 支持根据名称创建方法：
```python
method = MethodRegistry.create_method(wb.method_name)
```

---

## 📊 数据库 Schema

```sql
CREATE TABLE working_blocks (
    id TEXT PRIMARY KEY,
    project_name TEXT NOT NULL,
    block_id TEXT NOT NULL,
    method_name TEXT NOT NULL,  -- 新增字段
    status TEXT NOT NULL,
    config_json TEXT,
    result_json TEXT,
    output_path TEXT,
    prev_ids TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🔄 数据流

```
创建 WorkingBlock
  ↓
设置 method_name
  ↓
保存到数据库
  ↓
Worker 读取
  ↓
根据 method_name 创建方法
  ↓
执行方法.poll()
```

---

## 🔗 相关文件

- `setup_database.py`
- `videogen/dao/working_block_dao.py`
- `videogen/pipeline/global_worker.py`
- `videogen/methods/registry.py`
- `videogen/schema/working_block.py`

