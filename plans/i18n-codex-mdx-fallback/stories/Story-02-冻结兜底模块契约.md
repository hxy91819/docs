---
kind: story
id: STORY-02
epic: EPIC-I18N-MDX-CODEX-FALLBACK
title: 冻结兜底模块契约
gate: COMPONENT
depends_on: [STORY-01]
updated: 2026-09-01
intent_version: 3
language: zh-Hans
---

# Story：冻结兜底模块契约

<!-- large-task-planning:vision -->
## 愿景

实现 Agent 可以只读取一份简洁契约，就知道怎样增强现有 Codex repair action、什么时候启动它、怎样把检查错误反馈回会话、怎样记录结果，以及什么范围的越界必须拦截。

<!-- large-task-planning:scope -->
## 范围

根据真实 fixture 实验确定增强现有 Codex action 的输入、输出、会话生命周期、日志事件和停止条件。明确它与严格 MDX oracle、现有 scope/受保护属性检查和 artifact 的接口、顺序、幂等性及失败转交；不得再创建第二个 Codex repair action。设计轻量检查器的最小职责：发现空文件、整篇删除、大段异常截断或删除；不做细粒度语义等价判断。把 Prettier 和 PR #153 作为可插拔实验辅助：只在临时副本运行，失败或无净收益就丢弃，不把自研规则或 formatter 变成默认依赖。定义 Codex Agent、Luna、max 的实验配置接口，以及本地驱动和 CI 子流水线的调用边界。即使具体数值尚未确定，也必须有可注入的硬超时和最大尝试上限，禁止无限重试。

<!-- large-task-planning:key-decisions -->
## 关键决策

<!-- large-task-planning:decision owner=user -->
1. **轻量检查器优先拦截最严重的越界。**
   - 依据与建议：用户明确要求完成优先，不因小差异再次阻塞 CI。
   - 结果与影响：允许漏过细节问题；阈值和具体指标由真实实验校准。

<!-- large-task-planning:decision owner=user -->
2. **增强现有 Codex repair action，并复用一个 Agent 执行入口。**
   - 依据与建议：当前工作流已经使用 Codex，用户明确不希望再维护或接入第二套 Agent 修复动作。
   - 结果与影响：模块只约束现有 action 的输入、检查、反馈、日志和停止条件；不另造直接模型 API 层。

<!-- large-task-planning:decision owner=agent -->
3. **非 Agent 修复辅助默认关闭，只做可回退实验。**
   - 依据与建议：PR #153 的自研规则增加维护面；Prettier 初步探测不能修复本次损坏，且可能改变格式。两者都不应在没有增量证据时成为生产依赖。
   - 结果与影响：契约支持 `none`、`prettier` 和 `pr153` 实验臂；每个辅助失败都回到现有 Codex action，最终由 parser oracle 验收。

<!-- large-task-planning:acceptance-criteria -->
## 验收标准

- 契约明确现有 Codex action 增强后的启动条件、会话反馈路径、日志字段和可配置参数，且没有第二个 Agent 入口。
- 契约明确 Prettier/PR #153 可选辅助的输入输出、临时副本、幂等性和失败转交，不会重复或绕过现有修复。
- 检查器职责不包含完美语义比对，并有至少一个允许小差异的测试说明。
- 契约能覆盖 STORY-01 的真实 fixture，并为后续本地、CI 和经用户授权的生产接入提供同一入口。
