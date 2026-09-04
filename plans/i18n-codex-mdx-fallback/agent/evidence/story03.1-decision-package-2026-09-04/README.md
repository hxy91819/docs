# STORY-03.1 决策包目录说明（2026-09-04）

本目录是 STORY-03.1（汇总可行性并等待用户决策）交付给用户的决策包。只读汇编既有证据；不修改计划状态文件，不做生产授权。用户决策记录与计划回写由编排者在后半 Story 完成。

## 文件

- `feasibility-report.md`：决策包主文。主比较、taxonomy final_failure 根因、可选辅助对照、参数与环境事实、未知项汇总；全部数字带出处路径。
- `decision-options.json`：机器可读选项 A/B/C 与两个显式决策点（DP-1 多错误页协议、DP-2 300s 生产预算），每项含方案、风险、回退方式、工作量估计、STORY-04 解锁条件。

## 结论 → 证据指针

| 结论 | 数字/事实 | 证据路径（相对本目录上级 `evidence/`） |
| --- | --- | --- |
| 分母 696 页扫描、6 失败、失败分类 | `scanned=696`、`failures=6`（5 HTML comment + 1 错配 closing tag） | `story01-real-fixtures-2026-09-01/historical-scan.md` |
| fixture 体量与诊断 | anthropic-vertex 1,128 bytes/37 行（29:2）；taxonomy 446,554 bytes/3,790 行（1075:5） | `story01-real-fixtures-2026-09-01/oracle-output.json`、`README.md` |
| 真实 opt-in 最终轮（300s）逐臂结果 | no_assistance 0/2（9ms/685ms，exit 1）；enhanced 1/2（plugin success 210,131ms 2 轮 exit 0；taxonomy final_failure 343,056ms 2 轮 exit 0，checker pass，recheck compile_failure 1416:339） | `story03-local-loop-2026-09-01/real-opt-in/experiment.ndjson` |
| 注入参数 | HARD_TIMEOUT_MS=300000、MAX_ATTEMPTS=2、AUXILIARY_MODE=none、gpt-5.6-sol/high、CODEX_HOME=/root/.codex | `story03-local-loop-2026-09-01/real-opt-in/commands.json` |
| token 成本（仅最终轮） | plugin：input 234,078（cached 193,664）/ output 2,641 / reasoning 762；taxonomy：input 442,580（cached 364,288）/ output 5,847 / reasoning 3,614 | `story03-local-loop-2026-09-01/real-opt-in/experiment.ndjson`（`turn.completed` usage，位于 codex_stdout_tail） |
| 120s 击杀轮 | 2 fixture × 2 尝试全 exit 124；240,057ms / 240,659ms（=2×120s 每尝试语义） | `story03-local-loop-2026-09-01/real-opt-in/archive-2026-09-04-timeout-120s/experiment.ndjson`、`real-opt-in/parameter-evolution.json` |
| 参数演化与授权 | 120s 不足 → 编排者授权 300s（实验测量迭代，非放宽验收）；MAX_ATTEMPTS 恒 2 | `story03-local-loop-2026-09-01/real-opt-in/parameter-evolution.json` |
| 2026-09-01 沙箱阻断轮（环境失败，非预算结论） | enhanced 臂 2 条 exit 124（240,073ms/240,650ms）；no_assistance 2 条 exit 1（9ms/635ms，parser 阶段即失败，未触及 agent/网络，与沙箱无关） | `story03-local-loop-2026-09-01/real-opt-in/archive-2026-09-01-sandbox-blocked/`、`parameter-evolution.json` |
| 离线 mock 回路行为证据（checker 拦截、fail-closed） | enhanced mock 2/2 success（23ms/1,999ms，不可比真实耗时）；整 Accordion 删除 → checker_intercepted；空 frontmatter → final_failure | `story03-local-loop-2026-09-01/experiment.ndjson`、`README.md` |
| 1416:339 为第二处既有错误 | 修复 1075 后 recheck 暴露 1416:339 / offset 155163；从冻结 fixture 仅删 1075 行复算得到同错误同 offset | `story03-local-loop-2026-09-01/real-opt-in/experiment.ndjson`；复算脚本与中间件在 `/data/code/openclaw/docs/.local/story031-scratch/` |
| agent 第 2 轮按协议拒绝扩大范围 | 会话记录原话"按'仅修指定诊断'要求未处理"，未作编辑 | `story03-local-loop-2026-09-01/real-opt-in/experiment.ndjson`（agent_message） |
| Prettier 3.9.6 探测：五类损坏未修复 | 5 合成样例 + 1 合法对照；损坏样例输出"基本不变"、严格 MDX 仍失败 | `prettier-mdx-probe-2026-09-01.md`；formatter 旁证 `mdx-formatter-probe-2026-09-01.md` |
| PR #153 head 与基线差异 | head `4d37f029f0`（"rescue unparseable translated MDX before attribute repair"）；落后 upstream/main（`c2f5491dc4`）26 提交（`git rev-list --count 4d37f029f0..upstream/main`=26）；未 rebase、真实 fixture 未复验 | 本地只读 git 复核（2026-09-04）；交付范围 `parallel-agent-review-2026-09-01.md` |
| 辅助执行器未实现 → fail-closed | AUXILIARY_MODE=prettier/pr153 写 `auxiliary_not_implemented` 并 final_failure | `story03-local-loop-2026-09-01/README.md` |
| personal 账号限制 | gpt-5.6-sol 400 不支持；usage limit 至 2026-10-02 17:00（账号级） | `story03-local-loop-2026-09-01/environment-diagnostic-2026-09-04.json` |
| 默认 CODEX_HOME 可用 | probe turn.completed；config 恰为 gpt-5.6-sol/high；未复制凭据 | `story03-local-loop-2026-09-01/real-opt-in/environment-diagnostic-2026-09-04-default-home.json` |
| CLI 版本漂移（未知项） | 实验 codex-cli 0.153.2 vs workflow pin `@openai/codex@0.146.1` | `story03-local-loop-2026-09-01/environment-diagnostic-2026-09-04.json`；`story01-real-fixtures-2026-09-01/README.md` |
| 决策门约束 | 实验后必须暂停等用户决策；STORY-04 在决策落盘前 blocked；补实验回 STORY-03 | `../plan-v2/agent/plan.json`（D-04）；`../plan-v2/agent/stories/STORY-03.1.json`（AC-01～AC-05）；`story02-contract-2026-09-01/contract.md` §5、§7 |

## 边界

- 实验结果不自动成为生产授权（plan-v2 boundaries；STORY-03.1 outcome）。
- 本目录所有耗时/token 数值为实验记录，不是生产常量。
- 复算 taxonomy 第二处错误的中间文件在 `/data/code/openclaw/docs/.local/story031-scratch/`（scratch，不入库依赖）。
