# STORY-01 真实故障基线（2026-09-01）

本目录冻结了 `translate full` 历史失败的可回放正文、严格 parser oracle、内容保留判据和最小实验记录。所有文件均为证据副本；没有修改 `docs/**`、workflow 或 i18n 记忆。

## 目录

- `fixtures/zh-CN/plugins-reference/anthropic-vertex.md`：历史树中的 HTML 注释损坏，1,128 bytes / 37 行。
- `fixtures/zh-CN/maturity/taxonomy.md`：历史树中的 `Accordion`/`div` 错配，446,554 bytes / 3,790 行。
- `fixture-manifest.json`：每个 fixture 的 run、source/translation commit、脱敏说明、oracle、保留判据和预期日志字段。
- `strict-mdx-oracle.mjs`：固定 `@mdx-js/mdx@3.1.1` 的严格编译 oracle；任一 fixture 失败时进程退出码为 1。
- `oracle-output.json`、`oracle-output-repeat.json`：两次回放结果；JSON 字节级一致。
- `experiment-schema.json`：无辅助、增强现有 Codex action、检查器拦截、最终失败四类记录契约。
- `experiment-baseline.ndjson`：当前无辅助基线实测（两个 fixture 均 `final_failure`，`exit_code=1`）。
- `historical-scan.md`：从历史翻译提交扫描 696 页的命令、版本和 6 个失败明细。
- `provenance/live-r2-stale-28273967200.md`：线上 R2 stale 发布故障单独记录。

## 复现

从仓库根执行：

```bash
FIX=plans/i18n-codex-mdx-fallback/agent/evidence/story01-real-fixtures-2026-09-01
node "$FIX/strict-mdx-oracle.mjs" \
  "$FIX/fixtures/zh-CN/plugins-reference/anthropic-vertex.md" \
  "$FIX/fixtures/zh-CN/maturity/taxonomy.md"
echo $?  # 1：两个输入均严格编译失败
cmp "$FIX/oracle-output.json" "$FIX/oracle-output-repeat.json"  # 0
node "$FIX/measure-no-assistance.mjs" \
  "$FIX/fixtures/zh-CN/plugins-reference/anthropic-vertex.md" \
  "$FIX/fixtures/zh-CN/maturity/taxonomy.md"
```

环境前提：Node 22+（本次实测 `v24.15.0`）；仓库已有 `@mdx-js/mdx@3.1.1`。若依赖未安装，在临时目录执行 `npm install --no-save --package-lock=false @mdx-js/mdx@3.1.1`，不要修改仓库依赖文件。oracle 输出的关键观察为：

| fixture | parser source | 位置 | 结果 |
| --- | --- | --- | --- |
| anthropic-vertex | `micromark-extension-mdx-jsx` | line 29, column 2, offset 641 | `Unexpected character ! before name`（原始 HTML comment） |
| taxonomy | `mdast-util-mdx-jsx` | line 1075, column 5, offset 114137 | `Unexpected closing tag </div>`，期待 `<Accordion>`（开标签 line 975） |

## Provenance 与限制

两份正文均是提交 `fe5cb011ff0996b6bf007ba1e8f26377f10e541a`（2026-06-27 03:42:57Z）的**精确文件副本**。该提交与历史 run `27629404260` 的时间和 locale shard 失败窗口一致；各文件 `x-i18n.source_hash` 指向 manifest 中列出的 source commit。先前下载的 21 个 artifact 只有 metadata（无正文、无 stderr/stdout 尾部），因此不能证明某一页属于某一 shard；本目录明确标记为“由真实历史翻译提交重建”，不伪装成 artifact 正文。

历史树严格扫描发现 6 个失败页面：5 个 HTML comment、1 个 mismatched closing tag。本目录保留其中各一页作为代表；超时、重试耗尽和上游/provider 失败无法从 metadata-only artifact 区分，manifest 中保持 `null`，留给后续测量，不预设阈值。

`28273967200` 的 `/zh-CN/channels/line` 是 R2 stale 发布故障，已单独记录，不能计入 MDX 修复率。

## 给 STORY-02 / READY 门禁的交接

- 入口：`.openclaw-sync/docs-mdx-repair.md`（修复约束/提示）与 `.github/workflows/translate-locale-reusable.yml` 的 `Check translated MDX` → `Repair translated MDX` → `Enforce translated MDX repair scope` → `Recheck translated MDX` 顺序；主路径只能增强这一个 `openai/codex-action@v1`。
- 环境：workflow 使用 Node 22、`@mdx-js/mdx@3.1.1`、Codex CLI `@openai/codex@0.146.1`；真实 action 还需要 `OPENCLAW_DOCS_AGENT_OPENAI_API_KEY` 或 i18n API key。本 Story 仅运行无辅助严格 parser，未伪造 action 成功率。
- 契约必须覆盖：HTML comment、错配/多余 closing tag；并保留 raw `<`、unquoted 属性、void 元素、JS expression 损坏的 fail-closed 分支，以及 `28273967200` 的发布后 live smoke。
- 内容门禁：frontmatter / `x-i18n.source_hash`、标题、代码 token、链接、组件 marker 和未诊断章节保持不变；修复仅限诊断 edit span。成功率分母排除 `not_run`，checker 拦截与最终失败分开计数。
- 未决风险：历史 artifact 缺正文导致逐 shard 映射不可证；Codex 超时/重试参数尚未测量；PR #153（head 即基线）和 Prettier 3.9.6 只可作为固定 fixture 的低成本对照，不得新增第二执行器或盲写 locale。

## 可选对照

已有 `prettier-mdx-probe-2026-09-01.md`、`mdx-formatter-probe-2026-09-01.md` 和 `parallel-agent-review-2026-09-01.md` 记录版本与结果；它们使用合成输入或范围复盘，不能替代本目录的真实历史 fixture。
