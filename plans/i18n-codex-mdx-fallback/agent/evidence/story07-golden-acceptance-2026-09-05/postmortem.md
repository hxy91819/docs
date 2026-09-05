# 线上复盘：生产修复链 `--full-auto` 静默失效与演练收敛（AC-02/AC-03）

- 仓库：openclaw/docs（分支 `fix/i18n-mdx-syntax-repair`，验收 commit `5a6345abb8`）
- 日期：2026-09-05
- 输入：drill 1 run [33932528630](https://github.com/openclaw/docs/actions/runs/33932528630)（failure→根因）、drill 2 run [33933503869](https://github.com/openclaw/docs/actions/runs/33933503869) / [33934414308](https://github.com/openclaw/docs/actions/runs/33934414308)（dispatch 工具链缺口）、drill 3 run [33935656061](https://github.com/openclaw/docs/actions/runs/33935656061)（success）
- 取证方式：全部为只读（`git log -S` / `git show` / `gh run view --json` / artifact API 只读查询）；命令与输出摘要附后

## 1. 发现：`--full-auto` 与 CLI 0.146.1 不兼容（drill 1）

drill 1 在 runner 上实证：`codex-args: '["--full-auto"]'` 被 pin 版本 `@openai/codex@0.146.1` 拒绝，**agent 从未启动**。relay 的 classification 机制将其诚实归类为 `agent_failure`，"Fail unless classification is success" 步骤让 job 转红，Translate/Finalize job skipped（abort 先于发布）。同 run artifact（real-codex 41,192B / offline 33,844B）先行上传，证据未丢失。

由此发现：**生产原 Repair 步使用同一写法且包着 `continue-on-error: true`**——若生产同样踩中该 CLI 拒绝，修复链会静默失效。

## 2. 时间窗分析（git log 只读取证）

生产 Repair 步与 CLI pin 的演化（`git log -S` on `.github/workflows/translate-locale-reusable.yml`）：

| 日期（UTC/local 混排，按 commit 时区） | commit | 事件 |
| --- | --- | --- |
| 2026-04-23 | `3378551b0b` "ci: repair translated docs mdx" | 引入 Repair translated MDX 步：`openai/codex-action@v1` + `codex-args: '["--full-auto"]'` + `continue-on-error: true`（当时无显式 CLI pin） |
| 2026-04-28 | `72c3f8c2f8` | pin `@openai/codex@0.125.0`（`--full-auto` 时代，flag 可用） |
| 2026-07-13 | `3b02065782` | pin → `0.144.3` |
| 2026-07-14 | `b4b8148112` | pin → `0.144.4` |
| 2026-08-01 | `8a7f3884b0` | pin → `0.146.0`（**窗口最早起点，若 0.146.0 已拒 flag**） |
| 2026-08-05 | `1f5f836841` (#123) | pin → `0.146.1`（**窗口保守起点：drill 实证 0.146.1 拒绝 flag**） |
| 2026-08-27 | `bcd59fd54b` (#138, upstream openclaw/docs main) | 移除生产 Repair 步的 `--full-auto` 并集中 CLI pin（`git show upstream/main:…yml` 中 full-auto 计数=0）→ **上游 main 修复链自此恢复** |
| 2026-09-01 | `4d37f029f0` | 本分支基点：**不含 #138**（`git merge-base --is-ancestor bcd59fd54b HEAD` → NOT ancestor）；生产 Repair 步仍为 `--full-auto` + continue-on-error（4d37f029f0 版 workflow L273-287，且 Check/Repair/Enforce/Recheck 四步 L257/276/292/302 全部 continue-on-error） |
| 2026-09-04 | `b2b8297521` (STORY-04) | 生产 relay 化：4 轮 × `--full-auto`（复制了旧步写法） |
| 2026-09-05 | `d200a4eaaa` | 本分支移除全部 8 处 `--full-auto`（生产 relay 4 轮 + validation 4 轮）；沙箱语义改 `sandbox: workspace-write` + `safety-strategy: drop-sudo` |

**疑似静默失效窗**：
- 上游 openclaw/docs main：**2026-08-05（pin 0.146.1）→ 2026-08-27（#138）约 22 天**；若 0.146.0 已拒 flag 则自 2026-08-01 起约 26 天。
- 本分支谱系（fork）：flag 存续至 2026-09-05（`d200a4eaaa`），但生产 relay 在此期间**只跑过 drill（runner 演练即拦截），未进入生产翻译运行**，故未造成新的生产暴露。

**静默机制**（为何未被及时察觉）：
1. Repair/Recheck 等四步全部 `continue-on-error: true` → agent 未启动不产生步骤级红。
2. 旧 `package_artifact.py::failure_reason`（4d37f029f0 版 L66-84）只产出泛化文案 "mdx repair failed"——**无法区分"工具链不兼容导致修复链全量失效"与"单页修复尝试失败"**。
3. 历史 artifact metadata-only（STORY-01 已知限制）：无正文、无 stderr/stdout 尾部，事后无法逐 shard 复核哪次运行的修复链失效。

**诚实边界**：
- 0.146.0 是否已拒绝 `--full-auto`：**未验证，待实验**（本地安装 0.146.0 探针可解）。
- 生产在该窗口内实际受影响的运行清单：**不可从 metadata-only artifact 证明**；如需精确影响面，须由上游 openclaw/docs 以完整日志核对（列入上游跟进项）。

## 3. 修复前后对比

**flag 修复（`--full-auto`）**：
- 前：drill 1 run 33932528630 → relay job failure，classification=agent_failure，agent 未启动（14 秒内失败，`Repair translated MDX` 步 00:20:36→00:20:50）。
- 后：`d200a4eaaa` 移除 8 处（沙箱语义由 `sandbox: workspace-write` + `safety-strategy: drop-sudo` 表达；测试改为负向断言 + sandbox/drop-sudo 计数）→ drill 3 run 33935656061 relay **success**（`classification=success`、`reason=frozen_fixtures_pass_strict_recheck`、`repair_mode=relay`、`rounds=1`）。

**单轮预算（120s → 300s → 600s）**：
- 120s（2026-09-04 真实臂首轮，`real-opt-in/archive-2026-09-04-timeout-120s/`）：2 fixture × 2 尝试全部 exit 124 硬超时击杀；plugin 的修复在被击杀前已在磁盘完成（candidate 已通过严格 compile）却因 exit≠0 fail-closed 未收割——**实测证明 120s 会浪费已完成的修复**。
- 300s（编排者授权的实验测量迭代，`real-opt-in/parameter-evolution.json`）：plugin 1 轮 70.7s success；taxonomy 1 轮 166.6s success（接力协议同轮修复两处既有错误）。实测 n=2 最大 167s 已占 300s 预算 56%。
- 600s×4（D-10 用户决策，取代 D-09 的 300s 生产默认）：workflow env `MDX_REPAIR_HARD_TIMEOUT_MS=600000`、`MDX_REPAIR_MAX_ATTEMPTS=4`、步级 timeout 同步（translate-locale-reusable.yml L186-187、mdx-repair-validation.yml L46-47）；drill 3 relay 以该生产预算跑通。300s 保留为实验实测基线记录。

**dispatch 工具链缺口（drill 2）**：
- run 33933503869："Read source metadata" 失败（source sha 竞态）→ 钉 publish_ref commit 修复。
- run 33934414308："Fail failed locale artifact"（go 1.25→1.26 源仓库漂移 `2f3b9a28fd`；tsx dispatch 缺失 `1207b87161`）。
- 收敛：drill 3 全绿（offline ✓ / Real Codex relay ✓ / Translate canary 链 ✓ / Finalize 按设计跳过）。

## 4. 问题分流（AC-03）

**交给增强后的现有 Codex action（唯一 Agent 执行器）**：
- HTML comment 损坏（历史 5 页同类）；错配/多余 closing tag（含多错误页：接力协议下同轮修复首诊断+既有第二错误）；翻译正文小差异保留。全部经唯一 `openai/codex-action@v1` relay（≤4 轮有界）+ checker/scope/protected gate + 严格 recheck 处理。证据：GC-01/GC-02（golden-acceptance-report.md）。

**可选辅助（当前结论：均不纳入）**：
- Prettier 3.9.6：五类损坏均未修复（`prettier-mdx-probe-2026-09-01.md`）。
- @takazudo/mdx-formatter：无净收益旁证（`mdx-formatter-probe-2026-09-01.md`）。
- PR #153（head `4d37f029f0`）：落后 upstream/main 26 提交、未 rebase、真实 fixture 未复验（`story03.1-decision-package-2026-09-04/feasibility-report.md`）。
- 落盘：D-09 用户决策"方案 A——仅增强现有 Codex action"；辅助臂保持 fail-closed（`npm test` "unimplemented auxiliary arms fail closed before Codex" 断言 + workflow `Enforce auxiliary mode fail-closed` 步）。

**继续人工处理（不属于修复链职责）**：
- dispatch 模式基础设施缺口（source sha 竞态、go/tsx 工具链漂移）——由流程/依赖 pin 修复，不塞给 Agent。
- 上游同步跟进（见 §5）。
- 观察期内的修复率统计置信度、内容抽检与人工介入判定（D-08 模式）。

## 5. 遗留观察点（交观察期/上游）

1. **relay 第 2-4 轮 / 预算耗尽真实场景**：现仅 mock 覆盖（`tools/mdx-fallback-lab/test.mjs` relay protocol 测试 + pytest）；真实 runner 首次出现时产生首份现场证据（逐轮诊断已设计为全留档）。
2. **canary-release-summary live artifact**：机制在码（translate-locale-reusable.yml L951-975），待首次 `commit_locale=true` 真实发布。
3. **R2 smoke verified 现场记录**：机制在码（L928-949），drill 只读未发布，待真实发布验证。
4. **上游同步（openclaw/openclaw 与 openclaw/docs）**：
   - `.openclaw-sync/docs-mdx-repair.md` 为源同步镜像：STORY-04 的接力措辞修改需反哺上游，否则下次 source sync 覆盖（STORY-04 已登记风险）。
   - `--full-auto` 教训反哺：upstream openclaw/docs main 已由 #138 修复生产 Repair 步；建议上游核对 2026-08-05→08-27 窗口内运行的完整日志，确认修复链静默失效的实际影响面（metadata-only 无法自证）；openclaw/openclaw 源仓库如有同型步骤需同步旗标修正。
5. **0.146.0 对 `--full-auto` 的行为**：待实验（一条本地探针即可定窗口起点）。
6. **实验/生产模型组合等价性**：实验主证据为 gpt-5.6-sol/high（本地），生产与 drill relay 为 gpt-5.6/xhigh；drill 3 已证明生产组合在 runner 上通过冻结 fixture，但两组合的系统性对照仍属观察期数据（STORY-04 风险登记在案）。

## 6. 取证命令（只读）

```bash
# --full-auto 引入
git show -s --format='%h %ad %s' --date=iso-strict 3378551b0b
git show 3378551b0b -- .github/workflows/translate-locale-reusable.yml | grep -n "full-auto\|continue-on-error"

# pin 演化（对每个版本串做 -S）
for v in 0.125.0 0.144.3 0.144.4 0.146.0 0.146.1; do
  git log --format='%h %ad %s' --date=iso-strict -S "npm install -g @openai/codex@$v" \
    -- .github/workflows/translate-locale-reusable.yml | tail -1
done

# 上游修复与本分支谱系关系
git show -s --format='%h %ad %s' --date=iso-strict bcd59fd54b          # #138, 2026-08-27
git merge-base --is-ancestor bcd59fd54b HEAD; echo $?                  # 1 = 本分支不含 #138
git show upstream/main:.github/workflows/translate-locale-reusable.yml | grep -c full-auto   # 0
git show 4d37f029f0:.github/workflows/translate-locale-reusable.yml | grep -n "full-auto\|continue-on-error" | head

# 线上 run 只读查询
gh run view -R openclaw/docs 33932528630 --json conclusion,jobs
gh run view -R openclaw/docs 33935656061 --json conclusion,jobs
gh api repos/openclaw/docs/actions/runs/33935656061/artifacts --jq '.artifacts[].name'
```
