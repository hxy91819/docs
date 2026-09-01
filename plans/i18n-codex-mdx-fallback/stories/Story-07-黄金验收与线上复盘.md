---
kind: story
id: STORY-07
epic: EPIC-I18N-MDX-CODEX-FALLBACK
title: 黄金验收与线上复盘
gate: OBSERVE
depends_on: [STORY-06]
updated: 2026-09-01
intent_version: 2
language: zh-Hans
---

# Story：黄金验收与线上复盘

<!-- large-task-planning:vision -->
## 愿景

团队能在真实线上运行中判断这条兜底链是否真正减少流水线浪费，并把失败样本、耗时、重试和检查器误报转化为下一轮改进，而不是凭一次绿色 CI 宣布完成。

<!-- large-task-planning:scope -->
## 范围

在同一个 acceptance commit 上执行全部黄金案例；记录本地、独立 CI、正式 canary 和线上观察证据。线上观察作为后续模式持续收集成功率、失败类型、耗时、重试、人工介入和内容越界事件。完成窗口后更新决策文档、fixture、Codex action、可选辅助和 checker 设计，必要时插入修复 Story。

<!-- large-task-planning:key-decisions -->
## 关键决策

<!-- large-task-planning:decision owner=user -->
1. **线上真实验证可以作为后续观察复盘模式。**
   - 依据与建议：用户指出整条流水线耗时较长，不能把一次运行当作充分结论。
   - 结果与影响：发布完成不等于 Goal 完成，必须保留观察窗口和复盘入口。

<!-- large-task-planning:decision owner=agent -->
2. **最终结论以黄金案例和可追溯日志为准。**
   - 依据与建议：单纯 job 成功不足以证明内容安全或线上可用。
   - 结果与影响：所有案例和证据齐全前，Epic 不标记完成。

<!-- large-task-planning:acceptance-criteria -->
## 验收标准

- 全部黄金案例在同一 acceptance commit 上有通过或带原因的失败证据。
- 线上观察记录真实运行结果、失败样本、耗时和后续动作，且不泄露受控内容。
- 复盘结论明确哪些问题交给增强后的现有 Codex action、哪些可由可选辅助稳定处理、哪些继续人工处理；不以不断增加自研规则为默认方向。
- 计划、工作流文档和风险登记反映最新实验事实；未验证的细节仍保持待实验状态。
