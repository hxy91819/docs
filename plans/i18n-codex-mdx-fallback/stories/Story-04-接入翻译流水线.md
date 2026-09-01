---
kind: story
id: STORY-04
epic: EPIC-I18N-MDX-CODEX-FALLBACK
title: 接入翻译流水线
gate: COMPONENT
depends_on: [STORY-03.1]
updated: 2026-09-01
intent_version: 3
language: zh-Hans
---

# Story：接入翻译流水线

<!-- large-task-planning:vision -->
## 愿景

在用户明确选择并确认可行性后，真实翻译任务才把增强后的现有 Codex repair action 接入；它是唯一的 Agent 修复执行器，并通过轻量检查、有限反馈和严格复验保住已完成翻译。Prettier 或 PR #153 只有在用户决策明确批准且实验有净收益时才作为可选辅助接入；每个结果都能在 artifact 和日志中解释。

<!-- large-task-planning:scope -->
## 范围

仅在 STORY-03.1 的用户决策已落盘后，把增强后的现有 action 接到完整页面 MDX 诊断、artifact 打包和受保护属性修复的正确位置；若批准某个可选辅助，明确它只运行在临时副本或受控前置阶段，失败即回到现有 Codex action，避免重复写入或绕过 parser oracle；保留成功页面和失败页面的状态边界；接入结构化日志、失败摘要和敏感信息控制。只修改源工作流、控制脚本和测试，不手写生成 locale 页面。

<!-- large-task-planning:key-decisions -->
## 关键决策

<!-- large-task-planning:decision owner=agent -->
1. **将增强后的现有 Codex action 作为唯一、可观测的 Agent 阶段。**
   - 依据与建议：独立阶段便于回退、统计和复盘，但重复创建 action 会增加权限和维护面。
   - 结果与影响：artifact metadata 必须区分 Codex 修复、可选辅助、检查拦截和失败；不得出现第二个 Codex executor。

<!-- large-task-planning:decision owner=user -->
2. **优先保住已完成翻译，细节问题允许后续收敛。**
   - 依据与建议：用户不希望长流水线因小问题浪费前序翻译。
   - 结果与影响：未知或低严重度问题不强制扩大轻量检查器；发布策略仍需保留明确失败记录。

<!-- large-task-planning:decision owner=user -->
3. **正式接入不新增第二个 Codex action；可选辅助须有单独批准。**
   - 依据与建议：用户已确认增强现有 action；PR #153 和 Prettier 都需先证明净收益，并不能替代 Agent 或 parser oracle。
   - 结果与影响：即使 action 方向已确认，未完成 STORY-03.1 的主实验、用户决策和版本复验前也不改生产工作流；决策明确放弃辅助时才只接入增强 action，其他情况保持现有失败出口。

<!-- large-task-planning:acceptance-criteria -->
## 验收标准

- 正式翻译路径按实验确定的顺序调用增强后的现有 Codex action；可选辅助仅在用户批准且通过安全复验后启用。
- 正式路径不会新增第二个 Codex action；Prettier/PR #153 未批准或无净收益时不得产生生产改动。
- 既有 MDX、范围和受保护属性门禁继续运行，且不会被 fallback 绕过。
- fallback 结果、失败原因和修改路径出现在 artifact metadata、摘要或结构化日志中。
- 失败页面不会静默覆盖或删除其他成功结果，回退路径可在 CI 中复现。
