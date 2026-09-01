---
kind: story
id: STORY-03.1
epic: EPIC-I18N-MDX-CODEX-FALLBACK
title: 汇总可行性并等待用户决策
gate: USER_DECISION
depends_on: [STORY-03]
updated: 2026-09-01
intent_version: 2
language: zh-Hans
---

# Story：汇总可行性并等待用户决策

<!-- large-task-planning:vision -->
## 愿景

在正式修改翻译流水线之前，用户能看到一份基于真实 fixture 和实验数据的可行性结论，并明确选择增强现有 Codex action 的生产边界，以及是否保留 Prettier 或 PR #153 这类可选辅助。实验结果不会自动变成生产授权。

<!-- large-task-planning:scope -->
## 范围

汇总 STORY-01 至 STORY-03 的实验结果，必须比较无辅助与增强现有 Codex action；若已运行，再汇总 Prettier 或 PR #153 的单独对照，不要求组合矩阵。比较成功率、MDX 通过率、内容保留、耗时、重试、成本和维护风险；核对 PR head 是否已基于最新 `main`，记录 Prettier 版本、格式化失败和兼容性限制，形成给用户审阅的决策包。本 Story 不接入正式工作流、不发布 CI 生产变更、不修改生成 locale 页面；报告提交后暂停，直到用户明确决定。用户决定后，维护者必须把待决标记改为已确认、记录附加条件并刷新执行卡，随后才可解除 STORY-04 的阻塞。

<!-- large-task-planning:key-decisions -->
## 关键决策

<!-- large-task-planning:decision owner=pending -->
1. **Prettier 或 PR #153 是否进入正式链路，必须在实验后由用户决定。**
   - 依据与建议：PR #153 可能减少已知语法修复的模型调用，但带来自研规则维护成本；Prettier 初步探测没有修复本次损坏，且存在 MDX 版本和格式化范围风险。
   - 结果与影响：候选结果可以是仅增强现有 Codex action、增强 action 加某一辅助、修订辅助后纳入，或完全放弃辅助；用户决定前只允许实验和可行性分析。

<!-- large-task-planning:decision owner=user -->
2. **实验完成后必须暂停，等待用户确认是否落实方案。**
   - 依据与建议：用户已明确要求先分析可行性，再决定是否落实；增强现有 Codex action 会增加权限、耗时、成本和发布副作用，可选辅助还会增加工具链维护面，触发条件、失败出口和 artifact 契约必须在证据基础上确认。
   - 结果与影响：STORY-04 及其后续 Story 在本 Story 完成前保持 blocked；若用户要求补实验，回到 STORY-03，不得绕过决策门直接改生产工作流。

<!-- large-task-planning:decision owner=user -->
3. **正式链路只使用增强后的现有 Codex repair action 作为唯一 Agent 执行器。**
   - 依据与建议：用户已确认复用现有 action，避免重复维护第二套 Agent 修复入口。
   - 结果与影响：无论是否选择 Prettier 或 PR #153 辅助，生产工作流都只能有一个 Codex action；辅助失败时回到该 action 或保留明确失败。

<!-- large-task-planning:acceptance-criteria -->
## 验收标准

- 决策包必须比较无辅助与增强现有 Codex action，并对已运行的 Prettier/PR #153 探测标出样本分母、未知项和不可比项；未运行的辅助要说明原因，不把它们变成主路径前置条件。
- PR #153 的状态、head、与目标 `main` 的差异、测试结果和已知失败，以及 Prettier 的固定版本和探测结果均有可追溯记录；未复验的候选不能直接作为生产依赖。
- 报告包含明确的纳入、修订后纳入和放弃方案，以及每个方案的风险、回退方式和后续工作量。
- 用户的选择、附加条件或要求补实验已写入计划；在此之前不得开始 STORY-04 的正式代码接入。
- 用户选择落盘后，`USER_DECISION` 门的状态、批准的候选版本和 STORY-04 的领取条件彼此一致；要求补实验时仍保持阻塞并回到 STORY-03。
