# Grill with Docs

> 来源：Matt Pocock / mattpocock/skills (engineering/grill-with-docs)
> 触发词：grill with docs, 拷问并写文档, 对齐 CONTEXT.md

## 执行指令

对我当前的方案进行追问，同时：
1. 读取 `CONTEXT.md` 检查术语一致性
2. 每个决策达成后**实时更新** CONTEXT.md
3. 必要时创建 ADR（架构决策记录）

**追问规则（同 Grill Me）：**
- 每次一个问题，等我回答
- 给出推荐答案
- 可探索代码库

**文档更新规则：**
- 术语解析后立即写入 CONTEXT.md，不要攒批
- CONTEXT.md 只放术语定义，不放实现细节
- ADR 只在以下三者同时满足时创建：
  1. 决策难以逆转
  2. 缺乏上下文会让人困惑
  3. 确实存在有意义的取舍

**ADR 文件路径：** `docs/adr/0001-slug.md`

**ADR 模板：**
```md
# {简短标题}
{1-3 句话：背景、决策、原因}
```
