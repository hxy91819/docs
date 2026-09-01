# STORY-02 契约验收清单

用途：验证者可只读本目录完成 COMPONENT 门禁检查。`[ ]` 表示验证动作，不代表生产实现已完成。

## 契约覆盖

| 判据 | 契约位置 | 权威证据/入口锚点 | 结果 |
| --- | --- | --- | --- |
| 启动条件、输入/输出、顺序、唯一 Agent 入口 | `contract.md` §1 | `.openclaw-sync/docs-mdx-repair.md`；`translate-locale-reusable.yml` 的 Check → Repair → Scope → Recheck | [ ] |
| 两个真实 fixture 每个入口（启动/修复/检查/反馈/转交）有结论 | `contract.md` §2、`fixture-map.json` entries[0..1] | `story01-real-fixtures-2026-09-01/fixture-manifest.json`、`oracle-output.json` | [ ] |
| raw `<`、未加引号属性、void、JS expression 均 fail-closed | `contract.md` §2、`fixture-map.json` entries[2..5] | STORY-01 README 的边界说明；formatter probe | [ ] |
| checker 只拦空文件、整篇删除、大段截断/删除 | `contract.md` §3 | `实验契约.json` required_order/measurements；`fixture-manifest.json.content_retention` | [ ] |
| 至少一个允许小差异测试，明确不做完美语义比对 | `contract.md` §3 | taxonomy 临时副本测试说明（标点/短语变化应 pass） | [ ] |
| 错误回传同一会话、轮次/尝试有界、硬超时可注入 | `contract.md` §4 | `experiment-schema.json` rounds/repair_attempts/timeout_policy；workflow Codex step | [ ] |
| 辅助只有 none/prettier/pr153，临时副本、幂等、失败回 Codex | `contract.md` §5 | `实验契约.json` comparison_arms/required_order；三份 probe/review 证据 | [ ] |
| 日志字段对齐四类记录和 expected_log_fields | `contract.md` §6 | `experiment-schema.json`、`fixture-manifest.json.expected_log_fields` | [ ] |
| 本地、CI、授权生产共用同一入口；生产选择留给 STORY-03.1 | `contract.md` §7 | `实验契约.json.user_decision_gate`；STORY-02 decision_boundary | [ ] |

## 可执行验证

从仓库根执行。若依赖缺失，只能在 `.local/story02-scratch/` 临时安装，不改依赖文件。

```bash
FIX=plans/i18n-codex-mdx-fallback/agent/evidence/story01-real-fixtures-2026-09-01
node "$FIX/strict-mdx-oracle.mjs" \
  "$FIX/fixtures/zh-CN/plugins-reference/anthropic-vertex.md" \
  "$FIX/fixtures/zh-CN/maturity/taxonomy.md"
# 预期：退出码 1，两个真实 fixture 均 compile_failure

cmp "$FIX/oracle-output.json" "$FIX/oracle-output-repeat.json"
# 预期：退出码 0，oracle 输出字节级稳定

node -e 'JSON.parse(require("fs").readFileSync("plans/i18n-codex-mdx-fallback/agent/evidence/story02-contract-2026-09-01/fixture-map.json", "utf8")); console.log("fixture-map JSON ok")'
git diff --check -- \
  plans/i18n-codex-mdx-fallback/agent/evidence/story02-contract-2026-09-01
```

checker 行为测试（由 STORY-03 实现驱动）必须至少执行以下两个可观察断言：

1. taxonomy 临时副本只改一个标点/短语且保留章节、marker、链接时，`checker_result=pass`；
2. 删除 taxonomy 一个完整 Accordion 或把 anthropic-vertex 截成空 frontmatter 时，`checker_result=fail`，且 `final_outcome` 不得为 success。

## 未决项（不得在 STORY-02 自行定值）

- `HARD_TIMEOUT_MS`、`MAX_ATTEMPTS` 具体数值及 checker retention/deletion 阈值；
- 历史 metadata-only artifact 的逐 shard 页面映射；
- Prettier/PR #153 是否保留、固定版本/config、正式启用条件；
- 生产灰度范围、接入时机和发布授权。

这些项目必须进入 STORY-03 实验与 STORY-03.1 USER_DECISION；在决定前不得修改正式 workflow、增加依赖或发布。

## 交接检查

- [ ] `git status --short` 仅显示原有并行修改及本目录新增文件；
- [ ] 未修改 `docs/**`、`.github/**`、`.openclaw-sync/**`、workflow/脚本或计划状态文件；
- [ ] 验证者引用本目录 `contract.md`、`contract-checklist.md`、`fixture-map.json`，不把本契约误当生产授权。
