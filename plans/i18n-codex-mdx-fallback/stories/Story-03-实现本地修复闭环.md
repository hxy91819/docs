---
kind: story
id: STORY-03
epic: EPIC-I18N-MDX-CODEX-FALLBACK
title: 实现本地修复闭环
gate: COMPONENT
depends_on: [STORY-02]
updated: 2026-09-01
intent_version: 3
language: zh-Hans
---

# Story：实现本地修复闭环

<!-- large-task-planning:vision -->
## 愿景

在不启动整条 GitHub 流水线的情况下，开发者可以用一个本地脚本驱动“完整页面诊断—增强现有 Codex action—轻量检查—反馈重试—最终验收”的完整实验循环，并用证据判断 Prettier 或 PR #153 是否值得作为可选辅助。这个 Story 只产出实验原型和可行性数据，不授权生产接入。

<!-- large-task-planning:scope -->
## 范围

实现独立实验模块和本地驱动；接收 fixture、当前文件和 parser/checker 诊断；主实验只运行无辅助与增强现有 Codex action。Prettier 或 PR #153 仅在显式启用、成本可接受时各自单独运行，无法测量或没有代表样本就记录跳过原因，不做默认组合矩阵。启动现有 Codex repair action（实验组合 `Codex + Luna + max`）；每次修改后运行检查器，把失败信息回送同一会话。Prettier 只处理临时副本，输出不通过严格 parser 或内容检查就丢弃；PR #153 只作为可回退对照。超时、重试和模型参数可注入，默认值由实验记录而来。保存每轮修改、诊断、检查结果和最终文件。提供离线 mock 测试，以及显式启用、可真实启动本地 Codex 的集成测试。不得修改正式工作流或生成 locale 页面。

<!-- large-task-planning:key-decisions -->
## 关键决策

<!-- large-task-planning:decision owner=agent -->
1. **模块先独立于 GitHub Actions 实现。**
   - 依据与建议：本地脚本能缩短实验反馈，并隔离 CI 环境问题。
   - 结果与影响：CI 只调用稳定入口；模块可用 fixture 和真实 Agent 分别验证。

<!-- large-task-planning:decision owner=user -->
2. **真实 Codex 集成测试显式 opt-in。**
   - 依据与建议：用户要求本地真实验证，但普通测试不能依赖凭据或网络。
   - 结果与影响：缺少凭据时测试清晰跳过或报告环境状态，不把离线门禁变成网络门禁。

<!-- large-task-planning:decision owner=user -->
3. **只保留一个 Codex repair action；非 Agent 辅助不默认进入生产。**
   - 依据与建议：用户已确认增强现有 action；自研规则和一次性格式化都必须证明增量价值，不能因为“可能有用”而增加常驻层。
   - 结果与影响：实验模块必须能关闭 Prettier 或 PR #153，并保留同一份 oracle、日志和安全判据；实验结论提交 STORY-03.1 后暂停，不能自行进入生产。

<!-- large-task-planning:acceptance-criteria -->
## 验收标准

- 离线测试覆盖成功修复、检查器拦截和 Codex 反馈循环的可观察行为。
- 离线测试必须运行无辅助与增强现有 Codex action；Prettier/PR #153 若启用则分别记录阶段顺序、格式化失败和冲突结果，不要求组合覆盖。
- 设置实验环境后，本地命令能真实启动 Codex 并修复至少一个真实 fixture。
- 每次尝试都有结构化日志和可回放的输入/输出；修改范围可被后续 CI 检查。
- 模块失败时返回明确状态，不吞掉原始 parser 或 checker 诊断；没有净收益的辅助可以被完整关闭。
- 实验结束后只产出可行性报告所需证据；正式接入前必须等待用户决策。
