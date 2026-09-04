# STORY-03 本地修复闭环证据

本目录是独立实验回放，不被生产 workflow 引用。输入为 STORY-01 的两个真实失败 fixture，入口为 `tools/mdx-fallback-lab/index.mjs`；唯一 action 适配器对应现有 `openai/codex-action@v1` 参数协议，默认使用离线 mock。自 2026-09-04 D-09 用户决策起，Codex 轮次指令为**多轮接力协议**：每轮修复本轮反馈的全部 parser/checker 诊断；若前几轮已修复部分错误，继续修复剩余诊断直至页面通过严格编译；保持所有 must_preserve 项，不重写整页。轮数与时长仍由注入的 `MAX_ATTEMPTS`/`HARD_TIMEOUT_MS` 有界控制，非无限重试。

## 复现

```bash
CHECKER_CONFIG='{"min_retention_ratio":0.9,"max_deleted_run_lines":20,"max_tail_deletion_ratio":0.08,"max_bulk_deletion_ratio":0.1}' \
HARD_TIMEOUT_MS=5000 MAX_ATTEMPTS=2 AUXILIARY_MODE=none \
node tools/mdx-fallback-lab/index.mjs
```

```bash
cd tools/mdx-fallback-lab && npm test
```

缺少 `CHECKER_CONFIG`、`HARD_TIMEOUT_MS` 或 `MAX_ATTEMPTS` 时 fail-closed；上面的数值只属于本次实验注入，尚未授权生产默认值。`MDX_LAB_APPEND=1` 时 runner 把本轮记录**追加**到既有 `experiment.ndjson`（旧记录不覆盖）；缺省行为仍是整文件重写。`experiment.ndjson` 中每条记录同时写入 `repair_mode` 与顶层 `error_source/error_line/error_column`，并保留嵌套 `error` 对象。

`AUXILIARY_MODE=prettier` 或 `AUXILIARY_MODE=pr153` 当前未实现执行器，会在 Codex 前写入 `auxiliary_not_implemented` 并以 `final_failure` 结束；不会降级为“辅助后 Codex 成功”。

## 结果摘要

- `no_assistance`：两个真实 fixture 均保持 parser `compile_failure`，终态 `final_failure`。
- `enhanced_existing_codex_action`（离线 mock）：两个 fixture 均通过 checker、scope/protected gate 和严格 parser recheck，终态 `success`；taxonomy 需要两个有界 round（先移除诊断 stray close，再修复随后暴露的重复 label——这正是接力协议的逐轮推进）。
- `checker_interception`：删除完整 Accordion 的灾难性变体被 checker 拦截，终态不是 success，并携带同会话 feedback。
- `final_failure`：空 frontmatter 变体被 checker 拦截并在尝试耗尽后转为 `final_failure`。

## 真实 opt-in

真实调用只在 `MDX_LAB_REAL_CODEX=1` 时启用，使用 `/root/.nvm/versions/node/v24.15.0/bin/codex`；模型、推理强度与 CODEX_HOME 由 `MDX_LAB_MODEL`/`MDX_LAB_EFFORT`/`MDX_LAB_CODEX_HOME` 注入，`action.mjs` 将 stdin 设为 `ignore`，因此不会等待额外输入。当前权威轮（`real-opt-in/` 根目录）为 2026-09-04 多轮接力轮：`CODEX_HOME=/root/.codex`、`gpt-5.6-sol`/`high`、`HARD_TIMEOUT_MS=300000`、`MAX_ATTEMPTS=4`，两个 fixture 均真实修复成功——plugin-html-comment 1 轮 `success`（无回归），taxonomy-stray-close 1 轮严格 `compile_success`（D-09 接力协议下 AC 补充达成，详见下文专节）。其直接前轮（300s×2，taxonomy 为如实最终分类 `final_failure`）的 artifacts/commands/run 快照保存在 `archive-2026-09-04-final-attempts2/`。历史轮完整保存在 `real-opt-in/archive-2026-09-01-sandbox-blocked/`（沙箱网络阻断）与 `real-opt-in/archive-2026-09-04-timeout-120s/`（120s 预算不足实测）；参数演化与依据见 `real-opt-in/parameter-evolution.json`，环境自查见 `real-opt-in/environment-diagnostic-2026-09-04-default-home.json`。超时/重试值均为实验记录，不是生产常量。

本环境 CLI 仍输出 “Reading additional input from stdin...” 信息行，但 stdin 已为 `/dev/null` 等价的 ignore，进程未因 stdin 阻塞（2026-09-01 轮的剩余阻断是执行沙箱禁止访问 `wss://chatgpt.com/backend-api/codex/responses`，该问题在后续轮次已消失，见下文）。

`commands.json` 记录实际注入参数和固定阶段顺序；`artifacts/` 与 `real-opt-in/artifacts/` 保存 payload、metadata、changed/deleted 清单和 feedback，可脱离 workflow 回放。

### 2026-09-04 重试 probe（Result: blocked）

网络沙箱问题已消失（后端可达、鉴权通过），真实臂重跑因两个新的账号级阻断而停止：

1. 实验指定模型 `gpt-5.6-sol` 不在该 ChatGPT 账号可用模型列表（400 `invalid_request_error`）；账号 `models_cache.json` 实际提供 `gpt-reserve`、`gpt-5.6-terra`、`gpt-5.6-luna`、`gpt-5.5`、`gpt-5.4-mini`、`codex-auto-review`。
2. 账号 usage limit：受支持模型（`gpt-5.6-terra`、`gpt-5.5`）同样返回 "You've hit your usage limit … try again at Oct 2nd, 2026 5:00 PM"，与模型无关，换模型无法解除。

因此本轮未执行真实双 fixture opt-in：`real-opt-in/experiment.ndjson` 与 `real-opt-in/artifacts/` 仍为 2026-09-01 那轮（沙箱网络失败）记录，未追加或改写任何实验记录；probe 诊断见 `environment-diagnostic-2026-09-04.json`。复现命令不变，待账号配额恢复（2026-10-02 17:00 后）且模型问题由账号方解决时可直接按上文 `MDX_LAB_REAL_CODEX=1` 命令重放。离线回路本轮复验保持全绿（7/7 tests，离线驱动两 fixture 仍 `success`）。（该路线已被下一节默认 CODEX_HOME 路线取代；本节所述隔离 CODEX_HOME 目录现为 `archive-2026-09-01-sandbox-blocked/` 之前的共享历史。）

### 2026-09-04 默认 CODEX_HOME 轮（真实 opt-in 收尾；AC-03 达成）

**CODEX_HOME 切换原因**：上一轮使用的 `.local/story03-scratch/codex-home`（personal 账号副本）所属账号不支持 `gpt-5.6-sol` 且用量限制至 2026-10-02（见上节）。改用默认 codex home `/root/.codex`（不同账号，模型与配额均可用；其 config 恰为 `model=gpt-5.6-sol`、`effort=high`，与实验注入参数一致，模型可比性不变）。直接指向 `/root/.codex`，未复制任何凭据。

**Probe**：`printf 'reply with the single word OK' | timeout 150 env CODEX_HOME=/root/.codex codex exec --json -m gpt-5.6-sol -` 返回 `turn.completed`（stderr 仅已知无害的 "failed to refresh available models: timeout" 噪音）。诊断快照：`real-opt-in/environment-diagnostic-2026-09-04-default-home.json`。

**参数演化（120s → 300s）**：首轮仍用历史值 `HARD_TIMEOUT_MS=120000`，enhanced 臂 2 fixture × 2 尝试全部 exit 124——但环境已完全打通：agent 正常执行命令并编辑文件，plugin-html-comment 的修复在被击杀前已在磁盘完成（candidate.md 通过严格 compile），taxonomy 修好 1075 后需第二轮接力。实测证明 120s 不足以完成单轮真实修复 turn。经编排者决策授权改为 `HARD_TIMEOUT_MS=300000`（其余参数不变；属实验测量迭代而非放宽验收，仍有硬超时与尝试上限）。该 120s 轮完整存档于 `real-opt-in/archive-2026-09-04-timeout-120s/`；演化依据见 `real-opt-in/parameter-evolution.json`。

**最终结果（300000ms，MAX_ATTEMPTS=2，最终分类）**：

- `real-27629404260-zhcn-plugin-html-comment` × `enhanced_existing_codex_action`：**`success`（真实修复）**。2 轮、210131ms、exit 0；最终 turn usage：input 234078（cached 193664）/ output 2641 / reasoning 762 tokens。产物与原 fixture 的 diff 恰为最小修复：2 处 `<!-- openclaw-plugin-reference:manual-start/end -->` → `{/* … */}`；严格 `@mdx-js/mdx` recheck `compile_success`，checker/scope/protected-attribute 全部 pass。AC-03（真实修复至少一个真实 fixture）达成。
- `real-27629404260-zhcn-taxonomy-stray-close` × `enhanced_existing_codex_action`：**`final_failure`（最终分类，如实记录）**。2 轮、343056ms、exit 0，checker 两轮均 pass（内容保留）；但严格 recheck 仍 `compile_failure`。根因：该 fixture 在 STORY-01 报告诊断（1075 行多余 `</div>`）之外还存在第二处既有 MDX 错误（1416:339，`</div>` 与 `<span>` 不匹配）。agent 第 1 轮按最小修复协议修好 1075，第 2 轮面对 1416 反馈时明确表示按"仅修指定诊断"协议不扩大范围，未作编辑。按编排者决策，300s 结果即最终分类，不追加第三种超时值、不伪装成功。（修复协议 × 多错误 fixture 的交互是 STORY-03.1 可行性汇总的输入。）
- 两个 `no_assistance` 臂均按预期保持 parser `compile_failure`、`final_failure`。

本轮复现命令（仓库根；最终轮实际值，`real-opt-in/commands.json` 为机器可读版本）：

```bash
EV=$PWD/plans/i18n-codex-mdx-fallback/agent/evidence/story03-local-loop-2026-09-01/real-opt-in
CHECKER_CONFIG='{"min_retention_ratio":0.9,"max_deleted_run_lines":20,"max_tail_deletion_ratio":0.08,"max_bulk_deletion_ratio":0.1}' \
HARD_TIMEOUT_MS=300000 MAX_ATTEMPTS=2 AUXILIARY_MODE=none \
MDX_LAB_REAL_CODEX=1 MDX_LAB_MODEL=gpt-5.6-sol MDX_LAB_EFFORT=high \
MDX_LAB_CODEX_HOME=/root/.codex MDX_LAB_EVIDENCE=$EV \
node tools/mdx-fallback-lab/index.mjs
```

`real-opt-in/run.stdout`/`run.stderr` 保存本轮 runner 输出；`artifacts/` 保存 4 条记录的 payload、metadata 与 feedback 快照，可脱离 workflow 回放。（该轮的 artifacts/commands/run 快照已移入 `archive-2026-09-04-final-attempts2/`；根目录 `experiment.ndjson` 保留其 4 条记录并由下一轮追加。）

### 2026-09-04 多轮接力轮（HARD_TIMEOUT_MS=300000 × MAX_ATTEMPTS=4；D-09；taxonomy compile_success 达成）

**协议改造（D-09 用户决策）**：上一轮 taxonomy `final_failure` 的根因是“仅修指定诊断”协议与多错误 fixture 的交互——agent 修好首诊断后，面对下一轮反馈的 1416 既有错误明确按协议拒绝扩大范围。本轮把轮次指令改为**多轮接力**：每轮修复本轮反馈的全部 parser/checker 诊断；若前几轮已修复部分错误，继续修复剩余诊断直至页面通过严格编译；保持所有 must_preserve 项，不重写整页。`MAX_ATTEMPTS` 由 2 提到 4 作为注入预算上限（防不可修复页无限消耗），轮次循环仍由 `MAX_ATTEMPTS`/`HARD_TIMEOUT_MS` 注入控制，非字面无限重试。代码落点：`action.mjs` 新增 `ROUND_INSTRUCTION`/`buildRepairPrompt`（唯一指令来源，英文 prompt 与中文 feedback instruction 同源）；`index.mjs` 每轮把**当前** recheck 诊断（而非首轮原始诊断）喂回下一轮 prompt，四处 feedback instruction 统一引用 `ROUND_INSTRUCTION`；指令文本有测试断言（`tools/mdx-fallback-lab/test.mjs`，本轮 9/9 通过）。

**最终结果（300000ms × 4 轮上限，`MDX_LAB_APPEND=1` 追加记录，旧记录未覆盖）**：

- `real-27629404260-zhcn-plugin-html-comment` × `enhanced_existing_codex_action`：**`success`（无回归）**。1 轮、70743ms、exit 0；29/37 两行 `<!-- openclaw-plugin-reference:manual-start/end -->` → `{/* … */}`；严格 recheck `compile_success`，checker/scope/protected 全 pass。
- `real-27629404260-zhcn-taxonomy-stray-close` × `enhanced_existing_codex_action`：**`success`（AC 补充达成）**。1 轮、166576ms、exit 0；严格 `@mdx-js/mdx` recheck `compile_success`。修复 diff 仅两处：删除 1061 行的多余 `</div>`（解除 975 Accordion 的 div 失衡，parser 将失衡表面化报告在 1075:5），以及 1417 行重复的 `<span className="maturity-score-label">` 开标签（即上轮 1416:339 既有第二错误的成因）；内容保留 3789/3790 行，checker/protected-token 全 pass。上轮“仅修指定诊断”下拒绝处理的第二错误，本轮在接力指令下与首诊断同轮修复——未消耗额外轮次。
- 两个 `no_assistance` 臂均按预期保持 parser `compile_failure`、`final_failure`（无回归）。
- `experiment.ndjson` 现为 4 条上一轮记录 + 4 条本轮记录（共 8 条，追加式）；`artifacts/` 为本轮 4 条记录的 payload/metadata/feedback 快照；本轮 runner 输出在 `run.stdout`/`run.stderr`。

本轮复现命令（仓库根；`real-opt-in/commands.json` 为机器可读版本）：

```bash
EV=$PWD/plans/i18n-codex-mdx-fallback/agent/evidence/story03-local-loop-2026-09-01/real-opt-in
CHECKER_CONFIG='{"min_retention_ratio":0.9,"max_deleted_run_lines":20,"max_tail_deletion_ratio":0.08,"max_bulk_deletion_ratio":0.1}' \
HARD_TIMEOUT_MS=300000 MAX_ATTEMPTS=4 AUXILIARY_MODE=none \
MDX_LAB_REAL_CODEX=1 MDX_LAB_MODEL=gpt-5.6-sol MDX_LAB_EFFORT=high \
MDX_LAB_CODEX_HOME=/root/.codex MDX_LAB_EVIDENCE=$EV MDX_LAB_APPEND=1 \
node tools/mdx-fallback-lab/index.mjs
```

逐轮诊断全量留档：每条记录的 `feedback` 数组逐轮携带当轮诊断、violations、before/candidate sha256 与接力指令文本；若接力在 4 轮内未收敛，这些逐轮快照即是后期分析素材（本轮两 fixture 均在第 1 轮通过，未触发该场景）。
