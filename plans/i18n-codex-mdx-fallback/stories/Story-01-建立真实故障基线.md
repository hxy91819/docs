---
kind: story
id: STORY-01
epic: EPIC-I18N-MDX-CODEX-FALLBACK
title: 建立真实故障基线
gate: READY
depends_on: []
updated: 2026-09-01
intent_version: 3
language: zh-Hans
---

# Story：建立真实故障基线

<!-- large-task-planning:vision -->
## 愿景

后续实现不再依赖猜测。团队能用真实翻译流水线曾经失败的输入重放问题，并知道什么结果算修复成功、什么修改属于灾难性越界。

<!-- large-task-planning:scope -->
## 范围

回顾历史 CI 运行、artifact 和 MDX 诊断；优先回放 `27629404260` 的 metadata-only 失败和 `28273967200` 的线上 R2 stale 结果。同步审阅现有 Codex repair action、[PR #153](https://github.com/openclaw/docs/pull/153) 及其 head `4d37f029f0`，并记录 Prettier 的受限探测：确认各自能看到的故障边界、与现有受保护属性修复的调用顺序，以及已覆盖和未覆盖的场景。提取具有代表性的原文、译文、失败位置和日志，冻结为本地 fixture；历史 artifact 只有 metadata 时，用关联 source/translation commit 或可复现实验重建正文，并明确标记 provenance。为每个 fixture 写出 parser oracle、内容保留判据和需要保存的证据。建立最小实验记录格式，主比较无辅助与增强现有 Codex action；只有成本低且有代表 fixture 时，才单独记录 Prettier 或 PR #153 对照，不要求组合矩阵。合成样例只补足真实样本没有覆盖的分支。

<!-- large-task-planning:key-decisions -->
## 关键决策

<!-- large-task-planning:decision owner=user -->
1. **真实流水线失败优先作为 fixture 来源。**
   - 依据与建议：用户要求回顾真实链路，避免只用人工构造案例。
   - 结果与影响：fixture 提取完成前不冻结修复规则；历史日志需做脱敏并保留来源。

<!-- large-task-planning:decision owner=user -->
2. **超时和重试不在规划阶段定值。**
   - 依据与建议：用户要求以实际实验测量成功率、耗时和成本。
   - 结果与影响：本 Story 只建立测量方法，后续 Story 使用可配置参数。

<!-- large-task-planning:decision owner=user -->
3. **增强现有 Codex repair action，且不新增第二个 Codex 执行器。**
   - 依据与建议：用户已确认复用当前工作流中的 Agent；新增工作集中在完整页面触发、轻量内容检查、同会话反馈、有界重试和日志。
   - 结果与影响：fixture 和实验以增强后的现有 action 为主路径；不得把新 fallback 设计成另一套独立 Codex action。

<!-- large-task-planning:decision owner=agent -->
4. **PR #153 与 Prettier 不进入主路径，只在必要时做可选探测。**
   - 依据与建议：PR #153 的自研规则有维护成本；Prettier 的初步探测未修复本次五类损坏。主实验先验证增强 action；辅助只有在低成本且能回答具体问题时才运行。
   - 结果与影响：没有净收益的辅助不进入正式链路，也不因为缺少辅助对照而阻塞主实验。

<!-- large-task-planning:acceptance-criteria -->
## 验收标准

- 至少一组真实失败 fixture 可在本地重复触发原始 MDX 失败，并有来源、版本和脱敏说明。
- 每组 fixture 有稳定 parser oracle、内容保留判据和预期日志字段。
- 实验记录至少能区分无辅助、增强现有 Codex action、检查器拦截和最终失败；若运行 Prettier/PR #153 探测，则额外记录版本、阶段和结果，不要求组合实验。
- READY 门禁所需的代码入口、环境前提和未决风险均已写入 Agent 资料。
