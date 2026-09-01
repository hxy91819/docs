---
kind: story
id: STORY-05
epic: EPIC-I18N-MDX-CODEX-FALLBACK
title: 建立独立 CI 验证子流水线
gate: COMPONENT
depends_on: [STORY-04]
updated: 2026-09-01
intent_version: 3
language: zh-Hans
---

# Story：建立独立 CI 验证子流水线

<!-- large-task-planning:vision -->
## 愿景

在正式翻译工作流之外，可以单独触发增强后的现有 Codex repair action 和可选辅助实验，先验证 GitHub runner、权限、工具链和日志，再决定是否影响生产。

<!-- large-task-planning:scope -->
## 范围

建立可由 `workflow_dispatch` 和可复用调用触发的子流水线。它读取固定 fixture，安装与正式任务一致的 Codex/MDX 工具链，运行离线模块测试和可选真实 Codex 测试，验证增强现有 action 的单一执行入口、轻量检查和 MDX 验收；Prettier 与 PR #153 只作为固定版本的可选实验臂，失败即回退到现有 action。上传脱敏证据。默认不提交 locale、不触发线上发布；支持明确的实验参数和失败摘要。没有 STORY-03.1 的用户决策记录时，只允许 fixture-only 验证，不得模拟生产接入。

<!-- large-task-planning:key-decisions -->
## 关键决策

<!-- large-task-planning:decision owner=agent -->
1. **CI 验证先作为独立子流水线存在。**
   - 依据与建议：GitHub 环境、凭据和长耗时是独立风险，不能第一次接入就和生产翻译绑定。
   - 结果与影响：可以单独重跑和比较实验，生产工作流只在门禁通过后调用模块。

<!-- large-task-planning:decision owner=user -->
2. **真实 Codex 测试不能成为普通离线门禁。**
   - 依据与建议：用户要求本地真实测试，同时要保留无网络开发路径。
   - 结果与影响：CI 需要区分离线必过、真实 Agent opt-in 和环境失败三种结果。

<!-- large-task-planning:decision owner=agent -->
3. **CI 必须固定 Agent、可选辅助和工具链版本并证明单一执行入口。**
   - 依据与建议：PR #153 head、Prettier 版本和 Codex CLI 都会漂移；若不固定版本，CI 结果无法说明是哪一组合产生的。
   - 结果与影响：每次实验记录 action/CLI、可选辅助版本、目标基线和阶段顺序；生产接入前必须重跑用户批准的组合。

<!-- large-task-planning:acceptance-criteria -->
## 验收标准

- 子流水线可独立触发，并在干净 GitHub runner 上安装和运行模块。
- fixture 测试、MDX 验收、越界检查和日志 artifact 均有可下载证据。
- CI 证据能证明只有一个 Codex action，且可选辅助（如启用）先于它或失败后回退；最终 parser/scope gate 未被绕过。
- 默认运行不会修改生产分支或发布线上内容；实验模式的权限和输入明确。
- 真实 Codex 环境异常能分类报告，不伪装成 fixture 修复成功。
