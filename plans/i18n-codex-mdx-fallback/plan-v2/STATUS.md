# 翻译 MDX 修复兜底链 — 进展

> 这是供项目参与者阅读的视图，由结构化计划自动生成；请通过计划工具更新内容。

[查看目标与验收](SPEC.md)

## 此刻的判断

正在推进。已验证 4 / 8 项计划结果。

最近更新：2026-09-04。

## 正在推进

- **接入翻译流水线**：在用户明确选择并确认可行性后，真实翻译任务才把增强后的现有 Codex repair action 接入；它是唯一的 Agent 修复执行器，并通过轻量检查、有限反馈和严格复验保住已完成翻译。Prettier 或 PR #153 只有在用户决策明确批准且实验有净收益时才作为可选辅助接入；每个结果都能在 artifact 和日志中解释。

## 接下来

当前没有可直接开始的下一项结果。

## 之后的路线

没有尚在等待前置结果的工作。

## 需要关注

- **建立独立 CI 验证子流水线**：STORY-04 未完成
- **阶段化发布上线**：STORY-05 未完成
- **黄金验收与线上复盘**：STORY-06 未完成
- **实现本地修复闭环**：多错误页（1416:339 既有二次错误）的处理协议：仅修指定诊断 vs 多轮接力——STORY-03.1 用户决策点
- **实现本地修复闭环**：300s 实测超时是否作为生产预算提案——STORY-03.1 用户决策点
- **汇总可行性并等待用户决策**：真实模式下尚未出现第 2 轮及预算耗尽场景：该路径目前仅由离线 mock 测试覆盖（STORY-04/05 需保留该观察点）
- **汇总可行性并等待用户决策**：生产接入后修复率统计置信度依赖线上观察窗口（STORY-06/07）

## 已经得到的结果

- **建立真实故障基线**：worker=codexp/gpt-5.6-sol/effort=high，会话 mdx-fallback-20260901-story01-worker-1（provider 01a05c84-63b6-7e93-98e9-22654a9a5104，ACPX exit 0，continuity match，--non-interactive-permissions fail；provider 沙箱 danger-full-access 不独立强制边界，以提示词范围+编排者对账约束）。证据：plans/i18n-codex-mdx-fallback/agent/evidence/story01-real-fixtures-2026-09-01/（2 个真实 fixture：anthropic-vertex HTML comment 损坏、taxonomy Accordion/div 错配；strict-mdx-oracle.mjs 回放两次字节级一致；historical-scan 696 页 6 失败；experiment-schema 四类记录契约；无辅助基线双 fixture final_failure exit 1；provenance 含 28273967200 R2 stale）。未决：历史 artifact metadata-only 逐 shard 映射、超时/重试阈值留给后续 Story。
- **冻结兜底模块契约**：worker=codexp/gpt-5.6-sol/high 会话 mdx-fallback-20260901-story02-worker-1（provider 01a05c96-697c-79d3-a73e-45a4ef6f4730；首轮流含重叠片段致报告读取失败，同会话补发后 reader ok=True、continuity match）。证据：plans/i18n-codex-mdx-fallback/agent/evidence/story02-contract-2026-09-01/（contract.md/contract-checklist.md/fixture-map.json）。validator=pi/adapter默认 会话 mdx-fallback-20260901-story02-validator-1（provider 01a05c9f-0a07-7e28-9f0f-aad3292dbb39，策略 SHA-256 fddfca190e6c1609ac0096f87005dc48076d346a4e475266f24d24832f01df0c，ACPX exit 0，continuity match）：4 条验收逐条独立核实通过，无方向偏离、无第二入口、.github/.openclaw-sync 零改动。结论 PATCH_PROMPT 的处置（agent 决策）：validator 计划动作明确『契约级小缺口（§6 示例日志缺 repair_mode 与顶层 error_source/error_line/error_column 双写）不必回改冻结稿，评审通过置 done，补充要求写入 STORY-03 交接』；未回发 STORY-02 worker（其会话不得跨 Story），补充要求全文嵌入 STORY-03 worker 提示词：①日志额外输出 repair_mode+顶层 error 三元组双写；②checker 行为测试至少实现 contract-checklist 两条断言（改标点→pass；删 Accordion/空 frontmatter→fail 且 final_outcome≠success）；③HARD_TIMEOUT_MS/MAX_ATTEMPTS/checker 阈值可注入实测；④不改正式 workflow/.openclaw-sync/locale 页面。未决留档：辅助去留与生产参数 → STORY-03.1。
- **实现本地修复闭环**：STORY-03 完成。模块 tools/mdx-fallback-lab/ 六阶段闭环（npm test 7/7）；真实 opt-in 双 fixture：plugin-html-comment enhanced=success（2 轮/210s/exit 0，diff 恰 2 处 HTML 注释→MDX 表达式，strict oracle 独立复核 compile_success），taxonomy enhanced=final_failure（诚实分类：fixture 第 1416 行存在 STORY-01 诊断之外的第二处既有错误，agent 按仅修指定诊断协议未扩大范围）。参数演化 120s→300s 实测授权留档；CODEX_HOME=/root/.codex（personal 账号不支持 gpt-5.6-sol 且配额受限至 2026-10-02，默认账号可用）。validator=delegate/economy 结论 CONTINUE。
- **汇总可行性并等待用户决策**：用户决策 D-09 已落盘并经实测+validator 复核：方案 A 仅增强现有 Codex action（无辅助）；多错误页多轮接力协议（每轮修复反馈诊断直至编译通过或预算上限）；单轮 300s 实测、MAX_ATTEMPTS 注入默认 4。接力实测：双 fixture enhanced=success（plugin 1 轮 70,743ms；taxonomy 1 轮 166,576ms 修复 1061/1075+1417 两处既有错误，内容保留 3789/3790 行，strict oracle 独立复核 exit 0）。validator=delegate 结论 CONTINUE。决策包（含 A/B/C+DP-1/DP-2 分析与 PATCH 修正）存 evidence/story03.1-decision-package-2026-09-04/。
