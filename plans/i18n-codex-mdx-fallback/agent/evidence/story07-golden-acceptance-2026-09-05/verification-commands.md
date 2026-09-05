# 黄金判据本地验证命令清单（验收 commit `5a6345abb8`）

所有命令在 2026-09-05 于验收 commit 的工作树上实际复跑。命令均为只读（oracle/mocha 式测试/CLI 干跑输出到 /tmp 或标准输出，不写仓库、不触网、不需要凭据）。

## 1. 严格 MDX oracle 回放（GC-01 基线）

```bash
FIX=plans/i18n-codex-mdx-fallback/agent/evidence/story01-real-fixtures-2026-09-01
node "$FIX/strict-mdx-oracle.mjs" \
  "$FIX/fixtures/zh-CN/plugins-reference/anthropic-vertex.md" \
  "$FIX/fixtures/zh-CN/maturity/taxonomy.md"
echo $?   # 期望 1：两个真实 fixture 均严格编译失败（原始故障可复现）

cmp "$FIX/oracle-output.json" "$FIX/oracle-output-repeat.json"
echo $?   # 期望 0：两次历史回放字节级一致（oracle 稳定）
```

实测：oracle exit=1（anthropic-vertex 29:2 `Unexpected character ! before name`；taxonomy 1075:5 `Unexpected closing tag </div>`，与 `fixture-manifest.json` 逐字段一致）；cmp exit=0。

## 2. 无辅助基线（GC-01/02 对照臂）

```bash
FIX=plans/i18n-codex-mdx-fallback/agent/evidence/story01-real-fixtures-2026-09-01
node "$FIX/measure-no-assistance.mjs" \
  "$FIX/fixtures/zh-CN/plugins-reference/anthropic-vertex.md" \
  "$FIX/fixtures/zh-CN/maturity/taxonomy.md"
```

实测：exit 0（扫描器把 parser 失败作为数据输出）；两条记录均 `arm=no_assistance`、`parser_outcome=compile_failure`、`status=final_failure`（8.44ms / 600.86ms）。

## 3. 修复闭环协议测试（GC-03 checker 行为断言 + GC-04 离线路径 + 接力协议）

```bash
cd tools/mdx-fallback-lab && npm test
```

实测：**10/10 pass**（`ℹ tests 10 / ℹ pass 10 / ℹ fail 0`；验收 commit 原始复跑为 9/9，STORY-07 补入字面整篇删除断言后复跑）。关键断言：
- `checker permits a one-phrase/punctuation difference`（小差异放行，GC-03）
- `checker rejects a deleted Accordion and final outcome is not success`（大段删除拦截，GC-03）
- `checker rejects anthropic fixture reduced to empty frontmatter`（空文件级变体拦截，GC-03）
- `default checker configuration fails closed`（GC-03）
- `checker rejects a literal whole-file deletion and final outcome is not success`（字面整篇删除拦截：0 字节候选 fail-closed + 仅剩 frontmatter 零正文变体端到端拦截；`test.mjs` L40，GC-03 —— STORY-07 补）
- `unimplemented auxiliary arms fail closed before Codex`（辅助不纳入的 fail-closed，GC-02/复盘 §4）
- `relay protocol: mock rounds feed forward current diagnostics until strict compile passes`（接力协议，GC-02）
- `no-assistance preserves both real parser failures`（GC-01 对照）

## 4. i18n 控制面回归（GC-05 离线测试束的生产等价复跑）

```bash
python3 -m pytest .github/scripts/i18n/tests/ -q
```

实测：**158 passed in 19.70s**（覆盖 relay decide/report、canary decide/gate/r2-smoke/summary、package/finalizer 部分成功语义、validation 流水线结构断言）。

## 5. 单一 Codex 入口断言（GC-05）

```bash
python3 .github/scripts/i18n/mdx_repair_validation.py single-entry \
  --output-dir /tmp/story07-gates
echo $?   # 期望 0
```

实测：exit 0；`passed=true`、`single_entry="uses: openai/codex-action@v1"`、`action_count=4`、`no_second_executor=true`、`every_round_uses_relay_prompt=true`（与线上 `story06-live-drill-2026-09-05/single-entry.json` 一致）。

## 6. 严格 MDX oracle gate（GC-05）

```bash
python3 .github/scripts/i18n/mdx_repair_validation.py oracle-gate \
  --output-dir /tmp/story07-gates
echo $?   # 期望 0
```

实测：exit 0；`passed=true`，两 fixture expected/observed 全 match，两 repair reference `observed_outcome=compile_success`（即 STORY-03 真实修复快照独立复核通过）。

## 7. 真实 Codex opt-in 回放（GC-04；需凭据，按归档命令重放）

```bash
EV=$PWD/plans/i18n-codex-mdx-fallback/agent/evidence/story03-local-loop-2026-09-01/real-opt-in
CHECKER_CONFIG='{"min_retention_ratio":0.9,"max_deleted_run_lines":20,"max_tail_deletion_ratio":0.08,"max_bulk_deletion_ratio":0.1}' \
HARD_TIMEOUT_MS=300000 MAX_ATTEMPTS=4 AUXILIARY_MODE=none \
MDX_LAB_REAL_CODEX=1 MDX_LAB_MODEL=gpt-5.6-sol MDX_LAB_EFFORT=high \
MDX_LAB_CODEX_HOME=/root/.codex MDX_LAB_EVIDENCE=$EV MDX_LAB_APPEND=1 \
node tools/mdx-fallback-lab/index.mjs
```

状态：**待重放**（默认 CODEX_HOME 账号配额至 2026-10-02 17:00 恢复；`real-opt-in/commands.json` 为机器可读参数版本）。既有 8 条记录与 artifacts/（`real-opt-in/artifacts/`）构成可回放归档；离线部分（§3）不依赖凭据已全绿。

## 8. 线上 run 只读复核（GC-05/GC-06，非本地但可重放查询）

```bash
gh run view -R openclaw/docs 33932528630 --json conclusion,jobs   # drill 1: failure（gate 拦截 agent_failure）
gh run view -R openclaw/docs 33933503869 --json conclusion,jobs   # drill 2a: failure（source metadata）
gh run view -R openclaw/docs 33934414308 --json conclusion,jobs   # drill 2b: failure（工具链缺口）
gh run view -R openclaw/docs 33935656061 --json conclusion,jobs   # drill 3: success（offline+relay+canary）
gh api repos/openclaw/docs/actions/runs/33935656061/artifacts --jq '.artifacts[] | "\(.name) \(.size_in_bytes)"'
```

实测（2026-09-05）：33935656061 三 relevant job 全 success（Offline validation / Real Codex repair relay / Translate zh-CN shard 0/1，Finalize skipped=设计）；artifacts：`mdx-repair-validation-offline-33935656061`(33,846B)、`mdx-repair-validation-real-codex-33935656061`(41,150B)、`i18n-zh-cn-s0of1-4f695ddcef05fd33094d8c4350eb02cb01ef3d87`(171,913B)。

## 9. 复盘时间窗取证（只读 git）

见 `postmortem.md` §6（`git log -S` pin 演化、`git merge-base --is-ancestor bcd59fd54b HEAD`、`git show upstream/main:…` full-auto 计数）。
