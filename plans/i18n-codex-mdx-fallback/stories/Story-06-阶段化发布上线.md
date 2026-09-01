---
kind: story
id: STORY-06
epic: EPIC-I18N-MDX-CODEX-FALLBACK
title: 阶段化发布上线
gate: RELEASE
depends_on: [STORY-05]
updated: 2026-09-01
intent_version: 1
language: zh-Hans
---

# Story：阶段化发布上线

<!-- large-task-planning:vision -->
## 愿景

经过独立 CI 验证的 fallback 以小范围、可回退方式进入正式翻译流水线，先观察少量语言或页面，再扩大范围，不让一次实验改变全部发布面。

<!-- large-task-planning:scope -->
## 范围

制定启用开关、canary 范围、发布前门禁、回退动作和变更说明；先部署到单语言或单页路径，再逐步扩大。确认 Codex 权限、artifact 范围、日志保留和失败状态符合现有发布策略。把稳定后的操作说明写入工作流内部文档，不修改生成页面。

<!-- large-task-planning:key-decisions -->
## 关键决策

<!-- large-task-planning:decision owner=agent -->
1. **采用可逆的分阶段启用。**
   - 依据与建议：模型修复和 CI 环境都有长尾风险，先小范围能降低回退成本。
   - 结果与影响：正式全量启用前必须保留旧路径和明确关闭开关。

<!-- large-task-planning:decision owner=user -->
2. **发布参数以实验结果为准。**
   - 依据与建议：用户要求超时和重试不能凭空设定。
   - 结果与影响：本 Story 只落地已经测得的配置；未测参数保持显式待实验状态。

<!-- large-task-planning:acceptance-criteria -->
## 验收标准

- canary 能在不影响其他语言的情况下完成修复、检查、artifact 和发布验证。
- fallback 可被关闭并恢复原有失败路径，回退动作经过演练。
- 发布摘要明确列出 Codex 修复、检查拦截、失败页面和剩余风险。
- 生产接入前 RELEASE 门禁所需的 CI、权限、范围和文档证据齐全。
