---
name: tdd
description: 测试驱动开发，红-绿-重构循环，垂直切片而非水平切片，通过公共接口验证行为。触发词：tdd、red-green-refactor、先写测试。
---

# TDD 过程控制

> 来源：Matt Pocock / mattpocock/skills (engineering/tdd)
> 触发词：tdd, red-green-refactor, 先写测试, 测试驱动

## 核心理念

测试应通过**公共接口**验证行为，而非验证实现细节。好的测试读起来像规格说明书——描述系统「做什么」而非「怎么做」。

## 禁止：水平切片

```
WRONG（水平切片）:
  RED:   test1, test2, test3, test4, test5  ← 一口气写所有测试
  GREEN: impl1, impl2, impl3, impl4, impl5  ← 一口气写所有实现

RIGHT（垂直切片 / Tracer Bullet）:
  RED→GREEN: test1 → impl1
  RED→GREEN: test2 → impl2
  RED→GREEN: test3 → impl3
```

水平切片产出的测试不可靠——批量写的测试验证的是**想象的行为**而非**实际的行为**。

## 工作流

### 1. 规划
- [ ] 确认接口变更
- [ ] 确认要测试的行为（排优先级）
- [ ] 识别 Deep Module 机会
- [ ] 列出行为清单（非实现步骤）
- [ ] 获得用户审批

### 2. Tracer Bullet（示踪弹）
写**一个**测试，确认**一个**行为：
```
RED:   写测试 → 失败
GREEN: 最小代码通过
```

### 3. 增量循环
```
RED:   下一个测试 → 失败
GREEN: 最小代码通过
```
规则：一次一个测试、只写够通过当前测试的代码、不预判未来测试。

### 4. 重构
全部测试通过后：
- [ ] 提取重复代码
- [ ] 加深模块（把复杂性藏到简单接口后面）
- [ ] 每步重构后跑测试
- [ ] **禁止在 RED 状态重构**

## 每个循环检查

```
[ ] 测试描述行为，非实现
[ ] 测试只用公共接口
[ ] 测试能在内部重构后存活
[ ] 代码是最小化的，只过当前测试
[ ] 无投机性功能
```

## Python 测试约定（MCP-Project）

测试文件放在 `tests/`，命名 `test_<模块名>.py`，用 pytest 运行：

```python
# tests/test_task_board.py
import pytest
from src.task_board import TaskBoard

def test_board_init_creates_working_status():
    """board_init 后 status 应为 working"""
    board = TaskBoard()
    board.init(task="test", context={})
    assert board.status == "working"

def test_L1_help_request_sets_blocked():
    """L1 求助应将 status 设为 blocked"""
    board = TaskBoard()
    board.init(task="test", context={})
    board.request_help_L1("What column?")
    assert board.status == "blocked"
    assert len(board.help_requests) == 1
```

运行：`python -m pytest tests/ -v`
