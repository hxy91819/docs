# STORY-06 真实 canary 演练证据（2026-09-05）

生产仓库 openclaw/docs runner 实测，验证 canary 开关、RELEASE gate 与修复接力：

- 演练 1（run 33932528630，failure）：`--full-auto` 被 codex CLI 0.146.1 拒绝（agent 未启动）→ 分类 agent_failure，诚实落档。**重要发现：生产原 Repair 步同写法 + continue-on-error → 升 pin 后生产修复链疑似已静默失效。**
- 修复：移除 8 处 codex-args --full-auto（d200a4eaaa）
- 演练 2（33933503869/33934414308，failure）：dispatch 模式工具链缺口——source sha 竞态（改用钉住 publish_ref commit）与 go 1.25→1.26 / tsx 缺失（2f3b9a28fd、1207b87161）
- 演练 3（run 33935656061，**success**）：offline ✓、Real Codex relay ✓（classification=success，frozen_fixtures_pass_strict_recheck，600s×4/none）、Translate canary 链 ✓（单 locale 单页隔离）、Finalize 按设计跳过（commit_locale=false 只读演练）

文件：classification.json（三态输出）、zh-CN-repair-report.json（逐轮诊断/repair_mode/顶层 error 三元组）、single-entry.json、oracle-gate.json。

## 遗留（进 STORY-07）
- canary-release-summary 的 live artifact 待首次 commit_locale=true 真实发布
- relay 第 2-4 轮/预算耗尽路径真实模式未触发（仅 mock）
