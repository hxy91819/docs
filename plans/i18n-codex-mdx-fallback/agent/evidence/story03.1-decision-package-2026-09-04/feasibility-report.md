# STORY-03.1 可行性决策包（主文）

日期：2026-09-04
分支：`fix/i18n-mdx-syntax-repair`
状态：**可行性汇总，等待用户决策。实验结果不自动成为生产授权。** 本文件不修改计划状态文件，不代表任何生产接入决定。

## 0. 输入与证据边界

本文全部数字来自以下已落盘证据（只读引用，未改写）：

- 实验数据：`plans/i18n-codex-mdx-fallback/agent/evidence/story03-local-loop-2026-09-01/`（下称 STORY-03 证据目录），含 `experiment.ndjson`（离线 mock 回路 6 条）、`real-opt-in/experiment.ndjson`（真实 opt-in 最终轮 4 条）、`real-opt-in/archive-2026-09-01-sandbox-blocked/` 与 `real-opt-in/archive-2026-09-04-timeout-120s/`（两轮归档）、`real-opt-in/parameter-evolution.json`、环境诊断 ×3、`README.md`。
- 基线：`plans/i18n-codex-mdx-fallback/agent/evidence/story01-real-fixtures-2026-09-01/`（`historical-scan.md`：696 页 6 失败；`oracle-output.json`；`experiment-baseline.ndjson`；`README.md`）。
- 冻结契约：`plans/i18n-codex-mdx-fallback/agent/evidence/story02-contract-2026-09-01/contract.md`。
- 辅助对照：`plans/i18n-codex-mdx-fallback/agent/evidence/prettier-mdx-probe-2026-09-01.md`、`mdx-formatter-probe-2026-09-01.md`、`parallel-agent-review-2026-09-01.md`；PR #153 状态经本地只读 git 命令复核（见 §6.2）。
- 计划上下文：`plans/i18n-codex-mdx-fallback/plan-v2/agent/plan.json`（boundaries、D-01～D-08；尤其 D-04：实验后必须暂停等用户决策）。

诚实性约束：样本极小（真实臂 n=2），所有成功率都是**描述性记录，不是统计结论**；未知项显式标注"未知"；本文不给生产授权口径。

## 1. 样本与分母

- 分母来源：STORY-01 `historical-scan.md` 对历史翻译提交 `fe5cb011f` 的 zh-CN 树做严格 `@mdx-js/mdx@3.1.1 compile({jsx:true})` 扫描，`scanned=696`、`failures=6`（两次扫描 NDJSON 字节级一致）。失败分类：5 页 HTML comment 损坏 + 1 页错配/多余 closing tag。
- 实验样本：从 6 个失败页各取一页为代表，共 **2 个真实 fixture（占已知失败页 2/6）**：
  - `real-27629404260-zhcn-plugin-html-comment`（`plugins-reference/anthropic-vertex.md`，1,128 bytes / 37 行）→ 代表 HTML comment 类（5/6 页属此类）；
  - `real-27629404260-zhcn-taxonomy-stray-close`（`maturity/taxonomy.md`，446,554 bytes / 3,790 行）→ 代表错配 closing tag 类（1/6 页）。
  - 出处：`story01-real-fixtures-2026-09-01/README.md`、`oracle-output.json`、`fixture-manifest.json`。
- 泛化限制（显式声明）：HTML comment 代表页的 success 至多按"损坏类型相似"外推到同类 5 页，**未经同类其余 4 页实测**；taxonomy 代表页实测暴露为多错误页（见 §5），单页结论不能代表全类。

## 2. 主比较：无辅助 vs 增强现有 Codex action（真实 opt-in 最终轮）

权威轮：2026-09-04 默认 CODEX_HOME（`/root/.codex`）、`gpt-5.6-sol`/`high`、`HARD_TIMEOUT_MS=300000`、`MAX_ATTEMPTS=2`、`AUXILIARY_MODE=none`。出处：`real-opt-in/commands.json`、`real-opt-in/README`（story03 目录 `README.md`）与 `real-opt-in/experiment.ndjson`。

| 指标 | no_assistance（真实） | enhanced_existing_codex_action（真实） |
| --- | --- | --- |
| 样本分母 | 2/696 已知失败页 | 2/696 已知失败页 |
| 成功率（success / n） | **0/2（0%）** | **1/2（50%）** |
| plugin-html-comment | `final_failure`，parser `compile_failure`（29:2），9ms，exit 1 | **`success`**：2 轮、210,131ms（≈210s）、exit 0；严格 recheck `compile_success`；diff 恰为 2 处 `<!-- … -->` → `{/* … */}`；changed_paths 仅 `docs/zh-CN/plugins-reference/anthropic-vertex.md` |
| taxonomy-stray-close | `final_failure`，parser `compile_failure`（1075:5），685ms，exit 1 | **`final_failure`（如实最终分类）**：2 轮、343,056ms（≈343s）、exit 0；checker 两轮 pass（内容保留）；严格 recheck 仍 `compile_failure`（1416:339，第二处既有错误，见 §5） |
| checker / scope / protected gate | not_run（未进入修复阶段） | enhanced 两例均 pass；taxonomy 内容保留但 parser 终门禁拒绝 → 不算成功 |
| 轮次 | 无轮次（无修复） | 均 2 轮（MAX_ATTEMPTS=2，未放宽） |
| token 成本 | 无（未调用模型） | 见 §4（仅最终轮 usage 入档，全程总量未知） |
| fail-closed | 保持失败出口，exit 1 | exit 0 ≠ success；最终以 parser recheck 定分类（taxonomy 如实 `final_failure`） |

出处：`real-opt-in/experiment.ndjson` 全部 4 条 `final_outcome` 记录（fixture_id、experiment_arm、final_outcome、rounds、elapsed_ms、exit_code、checker_result、parser_outcome、changed_paths 字段逐一对应上表）。

补充对照（非真实臂，仅作行为证据）：

- 离线 mock 回路（story03 目录 `experiment.ndjson`）：enhanced 臂两 fixture `success`（plugin 1 轮 23ms；taxonomy 2 轮 1,999ms——**mock 时延，与真实耗时不可比**）；灾难性变体两条被 checker 拦截（整 Accordion 删除 → `checker_intercepted`，541ms，exit 1；空 frontmatter → `final_failure`，exit 1）。
- 120s 击杀轮归档（`real-opt-in/archive-2026-09-04-timeout-120s/experiment.ndjson`）：enhanced 臂 2 fixture × 2 尝试全部 exit 124，单 fixture 约 240,057ms / 240,659ms（= 2 × 120s 硬超时击杀）。
- 2026-09-01 沙箱阻断归档（`real-opt-in/archive-2026-09-01-sandbox-blocked/`，见 `parameter-evolution.json`）：enhanced 臂 2 条 exit 124（240,073ms/240,650ms）；no_assistance 2 条 exit 1（9ms/635ms，parser 阶段即失败，未触及 agent/网络，与沙箱无关），属执行沙箱网络阻断（环境失败），**不构成任何时间预算结论**。
  - 注：parameter-evolution.json 源记录的'4 条全部 exit 124'为概括不精确，以归档 ndjson（archive-2026-09-01-sandbox-blocked/）为准。

## 3. 耗时与参数演化（120s → 300s）

实测演化链（`real-opt-in/parameter-evolution.json`，三轮记录）：

1. 2026-09-01 隔离 CODEX_HOME、120s：enhanced 臂 2 条 exit 124（240,073ms/240,650ms）；no_assistance 2 条 exit 1（9ms/635ms，parser 阶段即失败，未触及 agent/网络，与沙箱无关），原因网络沙箱（环境失败，非预算结论）。
2. 2026-09-04 默认 CODEX_HOME、120s：环境已打通，agent 正常工作，但每轮在 120s 被击杀（2 fixture × 2 尝试全 exit 124）；plugin 的修复在被击杀前已完成于磁盘（candidate 已过严格 compile），仅因 exit≠0 fail-closed 未收割。**结论：120s 不足以完成单轮真实修复 turn。**
3. 2026-09-04、300s（编排者授权的实验测量迭代，仍有硬超时与尝试上限）：两 fixture 均跑满 2 轮，210s（success）/ 343s（final_failure）。

预算语义（由记录直接可算）：`HARD_TIMEOUT_MS` 为**每轮/每尝试**上限（120s 轮单 fixture ≈240s = 2×120s）；`MAX_ATTEMPTS=2` 恒定未放宽 → 300s 预算下单 fixture 最坏占用 ≈ 2×300s = **600s**（实测 343s 未触及）。

未测区间（未知）：120s–300s 之间是否存在更低可行值，未测（300s 轮中 210s 完成 success、343s 用满两轮，单轮耗时未单独入档）。

## 4. token 成本（从 experiment.ndjson 提取）

真实臂每 fixture 的 `codex_stdout_tail` 仅保留**最终一个 turn** 的 `turn.completed` usage（出处：`real-opt-in/experiment.ndjson`）：

| fixture（enhanced 臂） | input_tokens | 其中 cached | output_tokens | reasoning_output_tokens |
| --- | --- | --- | --- | --- |
| plugin-html-comment（success） | 234,078 | 193,664 | 2,641 | 762 |
| taxonomy-stray-close（final_failure） | 442,580 | 364,288 | 5,847 | 3,614 |

- **全程（两轮合计）token 总量：未知**——中间轮 usage 未保留在 ndjson 中，以上仅为最终轮快照。
- cached 占比高（最终轮 82.7% / 82.3%），但 cached token 的实际计费口径**未知**（本证据不含账单数据）。
- 环境 probe 消耗（`real-opt-in/environment-diagnostic-2026-09-04-default-home.json`）：单句 probe input 14,248 / output 5。

## 5. taxonomy final_failure 根因：第二处既有错误 + 协议交互

**事实链**：

1. STORY-01 冻结 oracle 只报告 taxonomy 的第一处 parser 错误 1075:5（多余 `</div>`，期待 `<Accordion>` 975:3-975:43）——出处 `story01-real-fixtures-2026-09-01/oracle-output.json`。严格 parser 在首个错误处停止，因此单次诊断**不能证明**该页只有一处错误。
2. 真实 enhanced 臂第 1 轮修好 1075 后，recheck 暴露同一文件第二处**既有**错误：1416:339，`Unexpected closing tag </div>, expected corresponding closing tag for <span> (1416:14-1416:68)`，offset 155163（出处：`real-opt-in/experiment.ndjson` enhanced 记录的 `parser_diagnostics`）。
3. 独立复核（本次决策包编制时，scratch 复算）：从冻结 fixture 原文仅删除 1075 行的 stray `</div>` 后再跑严格 oracle，得到与真实轮完全一致的 1416:339 / offset 155163。**结论：1416:339 是 fixture 原文固有的错误，不是 agent 引入的**（复算脚本与中间文件在 `.local/story031-scratch/`）。
4. 协议交互：本轮注入的修复指令为"仅修指定诊断"式最小修复协议。agent 第 1 轮按协议修好 1075；第 2 轮收到 1416 反馈后**明确按协议拒绝扩大范围、未作编辑**（其会话记录原话：'按"仅修指定诊断"要求未处理'，出处同 ndjson `agent_message`）。checker 两轮 pass（内容保留），最终因 parser recheck 失败如实分类 `final_failure`。

**"仅修指定诊断" vs "多轮接力" 的差异与影响**：

| 维度 | 仅修指定诊断（本轮协议） | 多轮接力（逐个 parser 错误继续，受 MAX_ATTEMPTS 约束） |
| --- | --- | --- |
| 本实验 taxonomy 结果 | 修好 1075，1416 留存 → final_failure | **未知**——接力协议从未实测：120s 轮第 2 轮接力被超时击杀；300s 轮第 2 轮是协议拒绝而非接力修复 |
| 修改面风险 | 最小，天然贴合 scope gate | 每多一轮扩大一次修改面；需逐轮诊断 + 硬上限约束 |
| 成本 | 实测 343s 后终止 | 轮次、时间、token 随错误数线性增长（幅度未知） |
| 与契约关系 | 符合 `contract.md` §1 '修复应落在诊断 edit span 或其最小必要配对 token 内' | 需要在反馈契约（§4 feedback 对象）中显式定义"接力到下一 parser 错误"语义，属契约修订 |
| 对 6 页失败面的含义 | 多错误页将继续 final_failure（该 6 页中是否还有其他多错误页**未知**——其余 4 页仅做过首次诊断扫描） | 理论上可提高多错误页成功率，但无实测数据支撑任何数字 |

此交互是决策点 DP-1（见 `decision-options.json`），本文只陈述事实与权衡，不代用户选择。

## 6. 可选辅助对照（均非主路径前置条件）

### 6.1 Prettier 3.9.6 探测

- 出处：`prettier-mdx-probe-2026-09-01.md`；`mdx-formatter-probe-2026-09-01.md`（MDX 专用 formatter 旁证）。
- 样本分母：**5 类合成最小损坏样例 + 1 个合法嵌套 MDX 对照**（伪造未闭合标签、真实元素丢闭合、游离闭标签、unquoted 属性值、属性名垃圾字符；另 HTML comment 样例）。**不是真实流水线 fixture。**
- 结果：五类损坏 Prettier 输出"基本不变"，严格 MDX 全部仍失败；HTML 注释仅可能调整空行、仍失败；合法 MDX 正常格式化并编译通过。`@takazudo/mdx-formatter@1.3.0-next.4` 五样例全部 `changed: false`；`@markdownkit/markdownkit@2.3.2` 单样例 format 失败（原文件未变）。
- 未知项：是否存在"Prettier 能带来净收益"的真实故障类别——探测结论为目前**无任何证据**支持，且后续若实验也只允许固定版本 + 临时副本 + 全门禁（契约 §5）。
- 不可比项：Prettier 的任务是格式化合法输入，不是修复损坏语法；与 Codex 修复臂的耗时/token/成功率**不可比**。
- 未在主实验运行的原因：探测已显示对五类损坏无修复能力；且实验驱动中 `AUXILIARY_MODE=prettier` 执行器未实现——当前会写入 `auxiliary_not_implemented` 并 fail-closed 结束，不会伪装成功（出处：story03 目录 `README.md`）。

### 6.2 PR #153（head `4d37f029f0`）

本地只读 git 复核（本次决策包编制时执行）：

- `git log --oneline -3 4d37f029f0`：`4d37f029f0 fix(i18n): rescue unparseable translated MDX before attribute repair`，父提交 `0c83a26afa`（即本地 `main`）。
- 与目标基线差异：`git rev-list --count 4d37f029f0..upstream/main` = **26**（upstream/main = `c2f5491dc4`）→ PR head 落后上游 main 26 个提交，**未 rebase、未在最新 main 上复验**。
- 与当前分支关系：`git merge-base 4d37f029f0 HEAD` = `4d37f029f0` 自身 → head 已包含在当前分支历史中，当前分支领先其 3 个提交。
- 交付范围与已知失败（出处：`parallel-agent-review-2026-09-01.md`）：parser 驱动的 MDX syntax repair、`package_artifact.py` 打包接入、路径安全、受保护属性偏移处理、合成回归测试；**未交付** Codex action 增强、轻量 checker、同会话反馈循环、真实流水线 fixture 验证。
- 样本分母：合成回归测试（其通过记录不在本仓库证据内，具体用例数**未知**）；真实双 fixture opt-in **未运行**。
- 未运行原因：`AUXILIARY_MODE=pr153` 执行器未实现（同 §6.1，fail-closed）；且 rebase/兼容性复核属未授权开销，按契约 §5 与计划 boundaries，PR #153 只是可跳过的低成本对照，不是主路径依赖。
- 不可比项：PR 未在新 main 上复验前，其行为与当前工具链（Node、`@mdx-js/mdx@3.1.1`、Codex CLI）的兼容性**未知**；不能与本实验的真实成功率直接对比。

**边界声明**：以上两个辅助的任何"未来收益"都没有本仓库真实 fixture 数据支撑；无论用户选择哪个方案，主路径都是增强后的现有 Codex action，辅助至多是可跳过的预步骤（契约 §5 转交语义）。

## 7. 参数与环境事实（生产接入时的影响项）

1. **超时**：120s 实测不足（全部 exit 124）→ 300s 实测可完成两 fixture 的全部轮次（210s / 343s）。300s 是否作为生产预算提案 = 决策点 DP-2；全部超时/重试值均为实验记录，不是生产常量（`parameter-evolution.json` 明示）。
2. **CODEX_HOME / 账号**：
   - personal 账号副本（`.local/story03-scratch/codex-home`）：不支持 `gpt-5.6-sol`（400 invalid_request_error），且账号 usage limit 至 2026-10-02 17:00，受支持模型同样被拒（出处：`environment-diagnostic-2026-09-04.json`）。
   - 最终轮改用默认 `/root/.codex`（不同账号，模型与配额可用；config 恰为 `gpt-5.6-sol`/`high`；未复制凭据；出处：`real-opt-in/environment-diagnostic-2026-09-04-default-home.json`）。
   - **生产影响项**：生产 workflow 需要具备模型访问权与足额配额的账号；当前实验运行在个人环境账号上，生产配额、计费与账号形态**未知**，需在 STORY-04/05 前确认。
3. **CLI 版本漂移（未知项）**：实验使用本地 codex-cli **0.153.2**（环境诊断记录）；生产 workflow 固定 `@openai/codex@0.146.1`（出处：story01 `README.md`）。两者行为差异未测，版本等价性**未知**，建议列入 STORY-05 CI 复验范围。
4. **fail-closed 行为汇总（各臂均验证）**：no_assistance 保持失败出口；超时击杀 → exit 124 final_failure（即使修复已在磁盘也不收割）；enhanced 臂 exit 0 但 recheck 失败 → 如实 final_failure；灾难性变体被 checker 拦截；辅助臂未实现 → `auxiliary_not_implemented` fail-closed。**未观察到任何"伪装成功"路径。**

## 8. 已知未知项汇总

- 全程（多轮合计）token 总量；cached token 计费口径。
- 多轮接力协议的成功率与成本（未实测）。
- HTML comment 类其余 4 页是否可修复（未实测）；6 页之外长尾损坏分布（历史 artifact metadata-only，逐 shard 映射不可证——story01 `README.md`）。
- 120s–300s 间的最小可行超时；单轮级耗时分解。
- PR #153 rebase 后的兼容性与真实 fixture 表现；PR 合成测试用例数。
- 生产账号/配额形态；codex-cli 0.153.2 与 workflow pin 0.146.1 的行为等价性。
- 离线 mock 臂的耗时数据（与真实不可比，仅行为证据）。

## 9. 决策选项

机器可读选项、两个显式决策点（多错误页协议 DP-1、300s 生产预算 DP-2）及各自风险/回退/工作量/STORY-04 解锁条件见同目录 `decision-options.json`。目录索引与逐结论证据指针见同目录 `README.md`。

## 10. 边界

本决策包不授权任何生产变更：不修改 workflow、不发布 CI 生产变更、不触碰生成 locale 页面。用户明确决策并按 D-04/AC-04 落盘回写后，STORY-04 才可解除阻塞；若用户要求补实验，按计划回到 STORY-03。
