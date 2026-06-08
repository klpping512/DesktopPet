---
title: "Temperature vs Top-P 对比"
type: tutorial
series: API参数入门
tags: [api, temperature, top-p, 参数对比, 小红书]
created: 2026-06-08
---

# Temperature vs Top-P

> ⚖️ API 入门 | 两个参数的区别，一张表说清楚

## 对比表

| 对比项 | 🔥 Temperature | 🧂 Top-P |
|--------|---------------|----------|
| **控制方式** | 调整概率分布的"平坦度" | 直接截断候选词范围 |
| **效果** | 数学上调整所有词的概率 | 物理上排除低概率的词 |
| **推荐用法** | 精细调整创意度 | 快速排除不合理的词 |

> 💡 **实操建议：** 先调 Temperature 控制整体创意度，再用 Top-P 收窄词汇范围做微调。大多数场景固定一个调另一个就够了。

#Temperature #TopP #参数对比
