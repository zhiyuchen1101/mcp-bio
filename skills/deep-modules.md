# Deep Modules（深度模块）

> 来源：John Ousterhout《软件设计的哲学》(2018)
> 触发词：deep module, 重构接口, 降低认知负担

## 定义

```
Deep Module（好的）:
┌─────────────────────┐
│   简洁的接口          │  ← 少量方法，简单参数
├─────────────────────┤
│                     │
│   深层的实现          │  ← 复杂性隐藏在背后
│                     │
└─────────────────────┘

Shallow Module（避免）:
┌─────────────────────────────────┐
│       庞大的接口                  │  ← 很多方法，复杂参数
├─────────────────────────────────┤
│   薄薄的一层实现                  │  ← 只是传递调用
└─────────────────────────────────┘
```

## 设计准则

- 能否减少方法数量？
- 能否简化参数？
- 能否把更多复杂性藏到接口后面？
- 接口是「做什么」，实现是「怎么做」

## 经典例子

- **Deep:** JavaScript 垃圾回收器 → 接口：无（自动），实现：极其复杂
- **Shallow:** 一个只做参数校验却要传 10 个配置项的函数

## MCP-Project 应用

当前问题：`r_session_bridge.py` 暴露 13 个 MCP tool → Agent 认知负担过重

重构目标：13 个 tool → 3 个 Deep Module

| Module | 接口 (Agent 看的) | 隐藏的复杂性 |
|--------|-------------------|-------------|
| DataModule | `load_data(source)` `get_schema()` | GEO 下载、格式检测、列名推断 |
| AnalysisModule | `run_analysis(type, params)` | DESeq2/limma 选择、设计矩阵 |
| VizModule | `plot(chart_type, data_ref)` | ggplot2、PNG、ANSI、缓存 |
