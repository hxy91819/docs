# STORY-07 黄金验收报告（GC-01..GC-06）

- 仓库：openclaw/docs（工作副本 origin=hxy91819/docs，分支 `fix/i18n-mdx-syntax-repair`）
- 验收 commit：`5a6345abb8`（HEAD，"STORY-06 done: 真实 canary 演练全绿（run 33935656061）"）
- 验收日期：2026-09-05
- 判据来源：`plans/i18n-codex-mdx-fallback/plan-v2/agent/plan.json` `golden_acceptance` GC-01..GC-06（只读引用）
- 本地复跑：所有离线黄金判据命令在验收 commit 上重跑通过，命令与结果见 `verification-commands.md`
- 纪律声明：未修改任何计划状态文件的 acceptance/handoff；未执行 git 写操作；未触发远端动作（gh 仅 `run view` / `api .../artifacts` 只读查询）

## 结论一览

| GC | 标题 | 结论 |
| --- | --- | --- |
| GC-01 | 真实 MDX 故障经增强现有 Codex action 修复 | **pass** |
| GC-02 | 增强 action 处理规则外的真实长尾故障 | **pass** |
| GC-03 | 轻量检查器拦截灾难性内容删除 | **pass** |
| GC-04 | 本地真实 Codex 集成测试可选且可回放 | **pass** |
| GC-05 | 独立 GitHub CI 子流水线验证真实 runner | **pass** |
| GC-06 | 阶段化发布和线上观察可回退 | **pass-with-conditions**（持续线上观察窗口未完成，如实标注） |

---

## GC-01 真实 MDX 故障经增强现有 Codex action 修复 — pass

**判据**（plan.json GC-01 oracle）：严格 `@mdx-js/mdx` 编译器对修复后页面返回成功；scope/protected-attribute gate 通过；原文/译文 fixture 和 source hash 可追溯。

**证据链**：

1. **真实 fixture（STORY-01 冻结，可追溯）**
   - `story01-real-fixtures-2026-09-01/fixture-manifest.json`：两个 fixture 的 run `27629404260`、translation commit `fe5cb011ff0996b6bf007ba1e8f26377f10e541a`、source commit 与 `x-i18n.source_hash`、脱敏说明、`must_preserve` 判据、预期日志字段。
   - `fixtures/zh-CN/plugins-reference/anthropic-vertex.md`：1,128 bytes / 37 行，sha256 `9eea41f0f9c5…`，损坏=29:2 HTML comment。
   - `fixtures/zh-CN/maturity/taxonomy.md`：446,554 bytes / 3,790 行，sha256 `1f4e4c8f604f…`，损坏=1075:5 错配 closing tag（开标签 975 行）。
   - **原始失败回放（验收 commit 上复跑）**：`node strict-mdx-oracle.mjs <两个 fixture>` → exit 1，逐字段与 `oracle-output.json` 一致；两次回放字节级一致（`cmp oracle-output.json oracle-output-repeat.json` → exit 0）。结果见 `verification-commands.md` §1。
2. **本地真实修复（STORY-03，D-09 接力协议轮）**
   - `story03-local-loop-2026-09-01/real-opt-in/experiment.ndjson` 记录 5/7（idx，0 起）：`enhanced_existing_codex_action` 双 fixture `success`，plugin 1 轮 70,743ms、taxonomy 1 轮 166,576ms，exit 0；strict recheck `compile_success`。
   - 修复 diff 最小化：plugin 恰 2 处 `<!-- … -->` → `{/* … */}`；taxonomy 仅删 1061 行多余 `</div>` 与 1417 行重复 `<span>` 开标签，内容保留 3,789/3,790 行（`story03-local-loop-2026-09-01/README.md` "2026-09-04 多轮接力轮"节）。
   - 修复后快照独立复核：`story06-live-drill-2026-09-05/oracle-gate.json` `repair_references[*].observed_outcome=compile_success, match=true`（验收 commit 上复跑 oracle-gate CLI → `passed=true`）。
3. **runner 真实接力修复（STORY-06 drill 3）**
   - run [33935656061](https://github.com/openclaw/docs/actions/runs/33935656061)（workflow_dispatch，openclaw/docs）job "Real Codex repair relay (opt-in)" success：`Check translated MDX`→`Repair translated MDX`（round 1 success）→`Enforce scope`→`Recheck` 全 success，rounds 2-4 正确 skip。
   - `story06-live-drill-2026-09-05/classification.json`：`classification=success`、`reason=frozen_fixtures_pass_strict_recheck`、`parser_outcome=compile_success`、`repair_mode=relay`、`rounds=1`、`changed_paths` 的 before sha256 与冻结 fixture sha256 逐字节一致（taxonomy `1f4e4c8f…`、anthropic `9eea41f0…`）→ runner 修复的正是冻结的真实故障输入。
   - `story06-live-drill-2026-09-05/zh-CN-repair-report.json`：逐轮诊断、`repair_stage_order`（parser→auxiliary→codex→checker→scope→protected_attribute→recheck→artifact）、violations 空。

**结论**：**pass**。同一真实故障输入在本地（gpt-5.6-sol/high）与生产 runner（gpt-5.6/xhigh，D-10 预算 600s×4）两条路径上均被唯一增强现有 Codex action 修复并通过严格编译。

---

## GC-02 增强 action 处理规则外的真实长尾故障 — pass

**判据**（GC-02 oracle）：至少一个非 PR153/Prettier 预设路径的真实页面，最终通过严格 MDX 编译和范围门禁，日志证明增强 action 处理了原始失败；失败时不伪装成功。

**证据链**：

1. **非预设路径选择**：taxonomy 的 mismatched closing tag 类不在 PR #153 rescue 预设内，且 Prettier 3.9.6 探测证明 formatter 对五类损坏"基本不变"（`mdx-formatter-probe-2026-09-01.md` 旁证、`prettier-mdx-probe-2026-09-01.md`）——该长尾只能由 Agent 修复。
2. **最终修复成功**：D-09 接力协议下 1 轮 166,576ms `compile_success`（GC-01 证据 2）；runner 复现 run 33935656061 relay success（GC-01 证据 3）。
3. **诚实处理 final_failure（taxonomy 300s×2 轮）**：
   - `real-opt-in/experiment.ndjson` 记录 3（idx）：`enhanced_existing_codex_action` × taxonomy = `final_failure`（343,056ms，checker 两轮 pass，recheck `compile_failure`）——如实落档，未伪装成功。
   - 根因留档：fixture 在 STORY-01 诊断（1075:5）之外存在第二处既有错误 1416:339（`</div>` 与 `<span>` 不匹配）；agent 第 2 轮按当时"仅修指定诊断"协议拒绝扩大范围（agent_message 原话在该记录内）。
   - 协议交互成为 D-09 用户决策输入（`plan.json` D-09；`story03.1-decision-package-2026-09-04/feasibility-report.md`），随后接力指令（`tools/mdx-fallback-lab/action.mjs` `ROUND_INSTRUCTION`）在同轮内修复两处既有错误。
4. **每轮证据可回放**：`real-opt-in/artifacts/real-27629404260-zhcn-taxonomy-stray-close-enhanced_existing_codex_action.json`（payload/metadata/feedback 快照）+ `-record.json`；`real-opt-in/run.stdout`/`run.stderr`；辅助版本=null（`auxiliary_mode=none`，`real-opt-in/commands.json`）。

**结论**：**pass**。真实长尾故障的失败中间态与最终修复态均有完整日志，未发生成功伪装。

---

## GC-03 轻量检查器拦截灾难性内容删除 — pass

**判据**（GC-03 oracle）：整篇删除、空文件和大段截断被识别并拒绝；小差异不因检查器过度严格而被拒绝。

**证据链**：

1. **npm test 行为断言（验收 commit 上复跑 9/9 pass；STORY-07 补入字面整篇删除断言后复跑 10/10 pass）**——`tools/mdx-fallback-lab/test.mjs`：
   - L17 `checker permits a one-phrase/punctuation difference`：小差异（"成熟度分类法"→"成熟度分类法。"）放行 → 不过度严格。
   - L23 `checker rejects a deleted Accordion and final outcome is not success`：大段删除（整节删除变体 `taxonomy-delete-accordion`）→ `checker_result=fail`、`final_outcome≠success`、同会话 feedback ≥1 条。
   - L30 `checker rejects anthropic fixture reduced to empty frontmatter`：空文件级变体（1,128 字节原文缩至 frontmatter，`action.mjs:19`）→ fail 且非 success。
   - L36 `default checker configuration fails closed`：缺省缺配置 fail-closed。
   - L40 `checker rejects a literal whole-file deletion and final outcome is not success`：字面整篇删除——0 字节候选 checker fail-closed（violation `empty_output`）+ 整篇删除变体（仅剩 frontmatter、零正文，复用既有 `anthropic-empty-frontmatter` mock 变体清空 taxonomy 正文）经修复循环端到端拦截 → `checker_result=fail`、`final_outcome=final_failure`、feedback 2 条。
2. **mock 变体端到端记录**：`story03-local-loop-2026-09-01/experiment.ndjson` 共 6 条，含 `checker_interception` 臂（taxonomy delete-accordion 变体 → `content_check=fail`、status `checker_intercepted`）与 plugin 增强臂空 frontmatter 变体（`content_check=fail` → `final_failure`，不伪装成功）；artifacts 快照在 `story03-local-loop-2026-09-01/artifacts/`。
3. **阈值注入**：`real-opt-in/commands.json` 与复现命令中 `CHECKER_CONFIG`（min_retention_ratio 0.9 / max_deleted_run_lines 20 / max_tail_deletion_ratio 0.08 / max_bulk_deletion_ratio 0.1）四阈值实测注入。

**STORY-07 补验收口（2026-09-05，分支 `fix/i18n-mdx-syntax-repair`）**：
- 原 pass-with-conditions 条件"字面'**整篇删除**（0 字节）'变体无独立命名断言"已收口：`tools/mdx-fallback-lab/test.mjs` L40 新增断言 `checker rejects a literal whole-file deletion and final outcome is not success`——0 字节候选断言 checker fail-closed（violation `empty_output`），并以"仅剩 frontmatter、零正文"整篇删除变体驱动修复循环，实测 `checker_result=fail`、`final_outcome=final_failure`、feedback 2 条；`npm test` 复跑 10/10 pass，原有 L17/L23/L30/L36 行号引用不变。
- 条件移除，GC-03 判定为 **pass**。

---

## GC-04 本地真实 Codex 集成测试可选且可回放 — pass

**判据**（GC-04 oracle）：显式开启真实 Agent 测试；保存会话与检查日志；有凭据时真实修复结果可编译且日志完整；无凭据时离线测试仍通过并给出可区分的跳过/环境状态。

**证据链**：

1. **显式 opt-in 门控**：真实调用仅在 `MDX_LAB_REAL_CODEX=1` 启用（`story03-local-loop-2026-09-01/README.md` "真实 opt-in"节）；注入模型/effort/CODEX_HOME（`MDX_LAB_MODEL`/`MDX_LAB_EFFORT`/`MDX_LAB_CODEX_HOME`），stdin=ignore（`tools/mdx-fallback-lab/action.mjs`）。
2. **可回放的 8 条真实记录**：`real-opt-in/experiment.ndjson`（2026-09-01 沙箱阻断 2+2 条 → 归档；2026-09-04 120s 击杀轮 4 条 → `archive-2026-09-04-timeout-120s/`；2026-09-04 300s×2 轮 4 条 → `archive-2026-09-04-final-attempts2/` 快照+根目录保留记录；2026-09-04 D-09 接力轮 4 条追加 → 共 8 条在档，`MDX_LAB_APPEND=1` 追加式不覆盖）。
3. **复现命令**：README 与 `real-opt-in/commands.json` 记录实际注入参数（`HARD_TIMEOUT_MS=300000 MAX_ATTEMPTS=4 AUXILIARY_MODE=none MDX_LAB_REAL_CODEX=1 MDX_LAB_MODEL=gpt-5.6-sol MDX_LAB_EFFORT=high MDX_LAB_CODEX_HOME=/root/.codex`）；参数演化与授权链在 `real-opt-in/parameter-evolution.json`（120s→300s 实测迭代、300s 保留为实验基线、D-09 轮 MAX_ATTEMPTS 2→4）。
4. **三态区分**：
   - 环境失败：`archive-2026-09-01-sandbox-blocked/`（网络沙箱阻断 `wss://chatgpt.com/backend-api/codex/responses`，诊断 `real-opt-in/../environment-diagnostic*.json`）——归档为环境失败，不计入预算结论。
   - 诚实 agent 失败：drill 1（run 33932528630）classification=agent_failure（见 GC-05）。
   - success：GC-01/GC-02 修复记录。
   - 无凭据/离线路径：`cd tools/mdx-fallback-lab && npm test` 9/9 全绿（不依赖凭据与网络；验收 commit 复跑通过）。
5. **真实臂重跑前提（诚实标注）**：默认 CODEX_HOME 账号当时配额受限至 2026-10-02 17:00（`real-opt-in/../environment-diagnostic-2026-09-04.json`）；复现命令与凭据恢复后可直接重放，归档记录在此期间作为回放证据。

**结论**：**pass**。可选、可回放、三态可区分均成立；账号配额属环境事实，不影响"机制可回放"判定。

---

## GC-05 独立 GitHub CI 子流水线验证真实 runner — pass

**判据**（GC-05 oracle）：GitHub runner 上的离线测试、严格 MDX gate、scope gate、单一 action 证据和日志 artifact 均可验证；默认不修改生产分支。

**证据链**：

1. **成功轮 run [33935656061](https://github.com/openclaw/docs/actions/runs/33935656061)**（2026-09-05T01:16Z，openclaw/docs，workflow_dispatch）：
   - Job "Offline validation (no secrets)" success（`gh run view` steps 实测）：Enforce auxiliary mode fail-closed → Install production toolchain → Run i18n control-plane regressions → Run mdx-fallback-lab fixture protocol tests → Run strict MDX oracle gate on frozen fixtures → Assert single Codex repair entry → Upload offline validation evidence，全 success，零 secret。
   - Job "Real Codex repair relay (opt-in)" success：Preflight agent credentials → Stage frozen fixture workspace → Check translated MDX → Decide relay → Repair（round 1 success）→ Enforce scope → Recheck success，rounds 2-4 正确 skip；`Record MDX repair relay outcome`/`Classify validation outcome` success；"Fail unless classification is success" 正确 skip（classification=success）。
   - classification 三态输出：`story06-live-drill-2026-09-05/classification.json`（budgets hard_timeout_ms=600000 / max_attempts=4 / auxiliary_mode=none，即 D-10 生产预算）。
2. **单一 action 证据**：`story06-live-drill-2026-09-05/single-entry.json`：`single_entry="uses: openai/codex-action@v1"`、action_count=4=prompt_count=rounds_budget、`no_second_executor=true`、`second_executor_tokens=[]`、`every_round_uses_relay_prompt=true`；验收 commit 上复跑 CLI exit 0 passed=true。
3. **严格 MDX gate**：`story06-live-drill-2026-09-05/oracle-gate.json`：`passed=true`，两 fixture expected/observed 逐字段 match（含 sha256/bytes/lines/offset），两 repair reference `compile_success`；验收 commit 复跑 exit 0。
4. **artifact 清单**（`gh api repos/openclaw/docs/actions/runs/33935656061/artifacts`，只读）：
   - `mdx-repair-validation-offline-33935656061`（33,846 bytes）
   - `mdx-repair-validation-real-codex-33935656061`（41,150 bytes）
   - `i18n-zh-cn-s0of1-4f695ddcef05fd33094d8c4350eb02cb01ef3d87`（171,913 bytes，canary locale artifact）
   - 失败轮 artifact 亦保留（drill 1 run 33932528630：offline 33,844B / real-codex 41,192B）→ "artifact 先传后置红"设计实证。
5. **失败轮诚实分类 + gate 生效（run [33932528630](https://github.com/openclaw/docs/actions/runs/33932528630)，failure）**：relay job 的 "Fail unless classification is success" 步骤 failure（classification=agent_failure，根因 `--full-auto` 被 CLI 0.146.1 拒绝、agent 未启动）；同 run 的 Translate/Finalize job 均 skipped → 失败先于发布被拦截，未写生产分支。
6. **权限与范围**：offline job 零 secret；`mdx-repair-validation.yml` 权限 contents:read、persist-credentials:false、无 push/发布步骤（STORY-05 handoff verification；`.github/workflows/mdx-repair-validation.yml`）。

**结论**：**pass**。成功轮与失败轮共同证明：三态分类诚实、gate 在分类≠success 时阻断发布、artifact 先行、单入口、runner 工具链与生产一致（codex pin 0.146.1、Node 22、@mdx-js/mdx 3.1.1、gpt-5.6/xhigh、600s×4）。

---

## GC-06 阶段化发布和线上观察可回退 — pass-with-conditions（观察窗口未完成，如实标注）

**判据**（GC-06 oracle）：启用 canary→完成翻译、修复、检查、artifact 和发布→观察线上页面与日志→必要时关闭开关并回退；线上页面通过 MDX/站点 smoke，失败可定位到文件和轮次，回退后原有路径可用。

**已成立部分**：

1. **canary 机制（translate-locale-reusable.yml）**：
   - 总开关 `mdx_repair_enabled`（L76/161-177，**默认 false = 原失败路径**）；范围 fail-closed 决策 `Decide canary MDX repair scope`（L299-313，`mdx_repair_canary.py decide`，locale/page 双重白名单）；relay 每轮以 `MDX_REPAIR_CANARY_ENABLED == 'true'` 为前置（L442 等）。
   - **RELEASE gate**：`mdx-repair-gate` job（L743-756，仅开关开且 locale 在 canary 白名单时以 `real_codex: true` workflow_call 复用验证子流水线；classification≠success → job fail）；`commit-locale` 条件（L757-770）要求 gate success（或显式 `canary_gate_failure_policy=fallback`）。
   - **R2 smoke**（run 28273967200 stale-R2 教训）：`Verify canary R2 content against artifact`（L928-949，`mdx_repair_canary.py r2-smoke`，比对 live h1 与 artifact 派生 h1；无法等待时记录显式 unverified reason 而非虚报成功；底层 `dispatch_r2_pages.py::verify_live_h1` L222-241）。
   - **发布摘要**：`Record canary release summary`（L951-975）→ `canary-release-summary` artifact（repair_mode/rounds、checker 拦截、failed paths、剩余风险、R2/Pages 完整性记录）。
2. **回退演练**：
   - 开关关闭等价性：输入默认关闭 = 修复链不启动、发布条件与 pre-canary 等价（workflow L4-6 注释契约；STORY-06 verification"表达式求值器+failure_reason 链路独立复核"+pytest 断言覆盖开关/canary 配置/回退分类）。
   - gate 阻断演练（drill 1）：classification=agent_failure → finalize skipped，"abort 先于发布"实测（GC-05 证据 5）。
   - 只读 canary 链演练（drill 3，run 33935656061）：单 locale（zh-CN）单页隔离的 Translate canary job success——canary scope decide → `Check translated MDX` success（MDX 无故障时 relay 全链正确 skip）→ `Prepare locale artifact`/`Upload locale artifact` success → Finalize 按 `commit_locale=false` 设计跳过（全程零生产写入）。
3. **dispatch 工具链缺口的修复链**（drill 2）：run [33933503869](https://github.com/openclaw/docs/actions/runs/33933503869)（"Read source metadata" 失败，source sha 竞态→钉 publish_ref commit 修复）、run [33934414308](https://github.com/openclaw/docs/actions/runs/33934414308)（"Fail failed locale artifact"，go 1.25→1.26 `2f3b9a28fd`、tsx 缺失 `1207b87161`）——三轮演练把基础设施缺口全部收敛为 drill 3 全绿。

**未完成部分（不得虚报）**：
- **持续线上观察窗口尚未开始**（plan.json D-08：发布完成≠Goal 完成）：观察窗口定义在 PR 合并后的首次 `commit_locale=true` 真实 canary 发布，首观察期内容 = 成功率/失败类型/耗时/重试/人工介入/内容越界事件的持续收集。
- `canary-release-summary` live artifact：机制在码（L951-975），但 drill 全程 `commit_locale=false`，无 live artifact 产生——待首次真实发布。
- R2 smoke 的 verified 现场记录：机制在码，drill 未发布故未触发 live 比对——待首次真实发布。
- relay 第 2-4 轮 / 预算耗尽的真实场景：drill 3 两 fixture 均第 1 轮收敛；该路径现仅 mock 覆盖（`test.mjs` L70-83 relay protocol 测试 + pytest）——待真实多轮场景产生首份现场证据。

**条件与归属**：
- 条件 1：PR 合并后开启观察窗口（归属：STORY-07 后续观察期，编排者/维护者按 D-08 模式持续收集，观察结论回写决策文档）。
- 条件 2：首次 `commit_locale=true` 真实 canary 发布时验证 canary-release-summary artifact、R2 smoke verified、发布与回退全链（归属：观察期首个发布轮）。
- 条件 3：真实 relay 第 2-4 轮/预算耗尽首现场证据（归属：观察期，出现即留档）。

**结论**：**pass-with-conditions**。机制、隔离、回退、阻断路径均有演练证据；观察窗口未完成如实列为未完项，不因机制演练全绿而宣布 GC-06 完整达成。
