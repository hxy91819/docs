# MDX 翻译修复兜底计划

<!-- large-task-planning:project-overview -->
## 项目概览

本项目为文档翻译流水线增强现有 Codex MDX repair action。用户已确认它继续作为唯一的 Agent 修复执行器，并增加完整页面诊断触发、轻量灾难性越界检查、有限反馈重试和结构化日志。所有参数先通过真实实验确定，日志用于后续复盘和改进。

PR #153 的自研解析器规则不作为默认生产依赖。Prettier 作为一次性格式化辅助只保留为受保护的实验对照；初步探测未修复本次已知损坏，因此不能把它当作 Codex 或严格 parser 的替代品。主实验只比较“现有基线 vs 增强 action”；只有在成本低且有代表 fixture 时，才单独探测 Prettier 或回放 PR #153，不做默认组合矩阵。实验完成后形成可行性报告，并在正式代码接入前等待用户明确选择是否启用任一辅助、采用哪些参数，或要求补实验。

本轮也筛选了其他候选：`@takazudo/mdx-formatter` 是最接近的 MDX 专用 formatter，但在合成损坏样例上解析失败时原样返回；`@markdownkit/markdownkit` 的一次混合样例也在解析阶段失败；Tree-sitter 可作为未来的容错诊断研究方向，仍不提供现成修复策略；markdownlint、remark-lint、eslint-mdx、mdformat、dprint 等主要解决风格检查或合法输入格式化。它们暂不增加新的实验臂，避免把“候选清单”膨胀成未经真实 fixture 支持的组合矩阵。证据见 [MDX formatter 探测](./agent/evidence/mdx-formatter-probe-2026-09-01.md)。

计划的硬门禁顺序是“完成实验 → 分析可行性 → 等待用户决策 → 正式实现”。执行门位于 STORY-03 与 STORY-04 之间：没有用户决策记录时，后续正式工作流修改、生产 CI 接入和发布均保持阻塞。

当前 Prettier 探测和并行 Agent 范围复盘分别记录在 [探测证据](./agent/evidence/prettier-mdx-probe-2026-09-01.md) 与 [复盘证据](./agent/evidence/parallel-agent-review-2026-09-01.md)；两者只提供实验输入，不解除门禁。

<!-- large-task-planning:epics -->
## Epic

- [EPIC-I18N-MDX-CODEX-FALLBACK：翻译 MDX 修复兜底链](./epics/EPIC-I18N-MDX-CODEX-FALLBACK.md)

<!-- large-task-planning:agent-entry -->
## Agent 入口

执行 Agent 从[项目进展](./项目进展.md)选择可领取的 Story，再读取 `agent/` 中同名执行卡及其直接引用。黄金验收、门禁和风险登记也位于 `agent/`。
