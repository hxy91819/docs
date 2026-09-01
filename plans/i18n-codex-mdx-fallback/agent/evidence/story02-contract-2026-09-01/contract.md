# STORY-02 兜底模块契约（冻结稿）

日期：2026-09-01
状态：仅定义可测试边界；不包含生产代码或发布授权。

本文件是实现 Agent 的唯一阅读入口。实现必须复用现有的 Codex repair action，不能创建第二个 Agent/action。所有“现有入口”均为只读锚点；本 Story 不修改这些文件。

## 1. 入口、启动条件与顺序

唯一入口是现有 workflow 的 `Repair translated MDX` 步骤（`openai/codex-action@v1`），其提示契约为 `.openclaw-sync/docs-mdx-repair.md`。本地驱动、独立 CI 子流水线和未来经用户授权的生产接入都必须调用同一入口参数协议，不得复制一套模型调用器。

按以下顺序执行，每一步产生可传给下一步的结构化结果：

```text
组装完整页面
  → 严格 parser/oracle（@mdx-js/mdx@3.1.1）
  → 可选辅助（none | prettier | pr153；默认 none）
  → 增强后的唯一 Codex action
  → 轻量 checker + scope gate + protected-attribute gate
  → 同一 Codex 会话反馈（若门禁拒绝，进入下一有界轮次）
  → 外部严格 parser recheck + artifact gate
  → success 或 per-file/per-shard final_failure
```

### 启动条件

只有同时满足以下条件才启动 repair action：

1. stale/跳过条件未命中，且 pending manifest 非空；
2. 完整页面已写入 locale 工作区；
3. 严格 MDX 检查返回 `compile_failure`，并有文件、行列/offset、parser source 的诊断；
4. 当前步骤的输入仍在允许的 locale/pending 路径内。

严格检查已通过、没有 pending 文件、仅有翻译提供方失败、或路径越界时，不启动 action：前两者是 `not_run`/成功分支，后两者直接按失败转交记录。锚点：`translate-locale-reusable.yml` 的 `Check translated MDX` → `Repair translated MDX` 条件；`.openclaw-sync/docs-mdx-repair.md` Required workflow 1–5。

### Action 输入/输出

输入是不可变的原始文件快照、pending manifest、严格 parser 诊断 JSON、locale/shard/source revision、受保护属性与 scope 规则，以及配置接口（见 §5）。Codex 只可写 manifest 中的 `docs/${LOCALE}/...` 文件，不得新增、删除或改名文件；修复应落在诊断 edit span 或其最小必要配对 token 内。

输出必须包括：

- 每个候选文件的内容 hash（before/after）、changed paths 和删除 paths；
- action/session/attempt/round 标识与退出码；
- parser、checker、scope、protected-attribute、最终 recheck 的结构化结果；
- 可供 `package_artifact.py` 使用的 payload 与 metadata。失败也要保留脱敏日志和失败 artifact，不能以 metadata-only 成功冒充页面成功。

现有 scope/protected-attribute 检查和 `package_artifact.py` 是外部门禁/打包接口，不由 checker 取代。锚点：`.github/workflows/translate-locale-reusable.yml` 的 `Snapshot translated MDX repair scope`、`Enforce translated MDX repair scope`、`Recheck translated MDX`；`.github/scripts/i18n/repair_mdx_protected_attributes.mjs`、`package_artifact.py`。

## 2. 诊断分类与 fallback 边界

下表冻结六类语法诊断。前两类来自 STORY-01 的真实历史正文；后四类是扫描器必须识别但不能猜测修复的边界。每行都明确 parser、修复、checker、反馈和转交结论。

| 类别与证据 | 启动/诊断 | Codex 修复结论 | checker/外部复验 | 失败转交 |
| --- | --- | --- | --- | --- |
| HTML comment 损坏；`anthropic-vertex.md:29:2`，`micromark-extension-mdx-jsx`，offset 641（`fixture-manifest.json`、`oracle-output.json`） | 启动；把完整诊断传入会话 | 只替换非法注释分隔符为 MDX 可表达形式，保留正文、marker、frontmatter 和行序；不得重排整页 | checker 只检查灾难性删除；再过 scope/protected gate 与严格 parser | 任一门禁失败则同会话反馈；耗尽后该文件/ shard `final_failure` |
| `Accordion`/`div` 错配；`taxonomy.md:1075:5`，期待 `<Accordion>`（同上） | 启动；保留 opening tag 行 975 与 closing token 诊断 | 仅移除/替换诊断出的 stray `</div>` 或补齐确定配对；后续 Accordion、分数、链接必须保留 | 同上；内容检查不得把语义重排当作成功 | 同上 |
| raw `<` 或翻译 prose 中伪造/未闭合 JSX | parser 诊断可定位时启动；无法区分文字与 JSX 时不得猜 | **fail-closed**：不自动转义/补标签；把原文和诊断交给同一 action，由人工/后续策略处理 | 不因 checker 通过而绕过严格 parser；最终 parser 失败即 `final_failure` | 同会话有界反馈后转交 shard 失败 |
| 未加引号属性值或属性名位置垃圾字符 | 启动；记录属性位置和原始 token | **fail-closed**，除非 parser 明确给出单一、局部且可逆的引号修复；不得改 protected attribute 值 | protected-attribute gate 是硬门禁；任何漂移均拒绝 | 同会话反馈 → 耗尽后 `final_failure` |
| void 元素未 self-close | 启动；记录元素及 parser 诊断 | **fail-closed**，不猜测元素是否应有 children；只有明确诊断的单 token 修复可由后续实验验证 | 严格 parser 必须重新通过；checker 不承担标签语义判断 | 同会话反馈 → `final_failure` |
| JS expression 损坏（`{...}` 内不可确定代码） | 启动仅用于记录 | **fail-closed**：禁止 Codex、formatter 或规则臂猜测/执行表达式；保留原文并转交 | parser/oracle 为唯一通过条件；checker 不做语义比对 | 立即记录不可修复诊断，按文件/shard 失败 |

上述六类之外的 provider 失败、Codex 硬超时/重试耗尽属于运行时终态，不伪装成 parser 成功；R2 stale（run `28273967200`，`/zh-CN/channels/line`）属于发布链路故障，必须走独立 live-smoke/发布转交，不能计入 MDX 修复率。历史 artifact 为 metadata-only，无法证明页面到 shard 的逐一映射，保持 `null` 未决。锚点：`historical-scan.md`、`fixture-manifest.json`、`provenance/live-r2-stale-28273967200.md`。

## 3. 轻量 checker：最小职责

checker 是灾难性内容保留检查，不是语义等价检查器，不比较译文质量、句法树等价性、措辞或格式美观度。它只在 action 写入后、外部 parser recheck 前运行；不修改文件。

以下判据必须可注入，具体数值由 STORY-03 实验校准；缺少配置视为 checker 配置错误并 fail-closed：

- `empty_output`：输出文件不存在、零字节，或源文件有正文而输出仅剩空 frontmatter/空白；
- `whole_document_deleted`：原有文件被删除，或输出相对原始正文的保留比例低于注入的 `min_retention_ratio`；
- `abrupt_truncation`：文件在末尾/单一连续区间异常截断，连续删除行数或尾部删除比例超过注入的 `max_deleted_run_lines` / `max_tail_deletion_ratio`；
- `abrupt_bulk_deletion`：多个连续段落/章节同时消失，删除比例超过注入的 `max_bulk_deletion_ratio`。

checker 输出 `{result: pass|fail, violations: [...], thresholds: {...}, before_sha256, after_sha256}`。`fail` 只表示灾难性越界，不能替代 scope、protected-attribute 或 parser gate。

允许小差异测试（必须保留）：以 `plans/i18n-codex-mdx-fallback/agent/evidence/story01-real-fixtures-2026-09-01/fixtures/zh-CN/maturity/taxonomy.md` 的临时副本为例，仅把一个中文句子的一个标点或短语改写，行数/章节/marker/链接均保留；checker 应返回 `pass`，即使译文与原文不具备完美语义等价。相反，删除 taxonomy 末尾一个完整 Accordion 章节或把 anthropic-vertex 正文截成 frontmatter，应返回 `fail`。该测试验证“允许漏过细节、只拦灾难性越界”的边界。

## 4. 会话反馈、幂等性与失败转交

### 同会话协议

每个 shard/调用只建立一个 Codex session。首轮输入包含 parser 诊断和原始快照 hash；action 写入后依次运行 checker、scope、protected-attribute 与 parser recheck。任何拒绝都生成统一 feedback 对象并在**同一 session 的下一轮边界**回传：

```json
{
  "round": 2,
  "path": "docs/zh-CN/maturity/taxonomy.md",
  "violations": [{"gate": "checker|scope|protected_attribute|parser", "code": "...", "detail": "..."}],
  "before_sha256": "...",
  "candidate_sha256": "...",
  "parser_diagnostics": [{"source": "mdast-util-mdx-jsx", "line": 1075, "column": 5}],
  "instruction": "仅修复诊断 span；保持所有 must_preserve 项；不要重写整页。"
}
```

反馈只携带必要诊断、路径和 hash，不回传完整敏感正文；日志按 evidence policy 脱敏。`round` 从 1 开始，`repair_attempts` 统计 action 写入尝试；轮次和尝试均受 `MAX_ATTEMPTS` 上限约束，硬超时受 `HARD_TIMEOUT_MS` 约束。两者必须是正整数注入参数；本 Story 不给出数值。达到任一上限、session 断开或 parser 仍失败即停止，不得无限重试。

### 幂等性

- 原始快照以 hash 固定；相同 `fixture_id + source_revision + experiment_arm + input_sha256` 重跑不得再次应用相同 edit span；
- 候选写入采用临时文件/原子替换，空候选或与当前 hash 相同则 no-op；
- `changed_paths`、`deleted_paths` 去重并排序；artifact metadata 以 attempt key 幂等更新，不追加重复记录；
- 辅助臂和 Codex 都不能重复执行已通过的修复；最终以 parser oracle、scope/protected gate 决定是否接受。

### 转交语义

- Prettier/PR #153 辅助失败、未改变输入、版本漂移或任一门禁拒绝：丢弃临时输出，回到**同一个** Codex action（不新建 Agent，不绕过既有修复）；
- Codex action 硬超时、session 错误或有界尝试耗尽：写入失败 artifact，标记对应 file/shard `final_failure`，保留原始诊断和退出码；
- scope/protected-attribute/parser 最终门禁失败：不得发布候选，按 shard 失败语义转交 finalizer；
- 发布 R2 stale 单独进入发布故障流程，不改变本模块的 MDX 成功率分母。

## 5. 实验配置与可选辅助

实验配置接口固定为 `agent=Codex`、`model=Luna`、`reasoning_effort=max` 的组合；实现可通过环境变量/输入参数注入标识，但不得偷偷切换模型。至少支持：`HARD_TIMEOUT_MS`、`MAX_ATTEMPTS`、`AGENT_ACTION_VERSION`、`PARSER_VERSION`、`CHECKER_CONFIG`、`AUXILIARY_MODE`、`AUXILIARY_VERSION` 和 `LOG_REJECTED_BODY`。其中超时与尝试上限无默认无限值；数值与是否启用辅助留给 STORY-03.1 用户决策。

`AUXILIARY_MODE` 只能是 `none`、`prettier`、`pr153`，默认 `none`，禁止组合臂：

| 辅助 | 输入/输出 | 临时副本与幂等 | 验收与失败转交 |
| --- | --- | --- | --- |
| `none` | 原始失败文件 + parser diagnostics；输出原始 hash | 无写回；重复运行 no-op | 直接进入唯一 Codex action |
| `prettier`（探测版本 `3.9.6`） | 单文件临时副本，`parser: mdx, proseWrap: preserve`；输出候选文本或 unchanged | 固定版本/config；候选 hash 相同即 no-op；不新增仓库依赖、不 `--write` locale | 候选必须依次过严格 parser、checker、protected gate；失败/无净收益丢弃，回到唯一 Codex action。探测显示五类损坏仍失败（`plans/i18n-codex-mdx-fallback/agent/evidence/prettier-mdx-probe-2026-09-01.md`） |
| `pr153`（head `4d37f029...`，仅对照） | 单文件临时副本运行 parser-guided deterministic repair；输出候选/diagnostics | 固定 head、临时目录和输入 hash；不扩张规则、不直接写 artifact | 候选必须过同一 parser/checker/scope/protected gates；rebase/版本漂移或失败即丢弃并回到唯一 Codex action。不得把它当第二 Agent 或默认依赖 |

辅助只提供候选，不拥有发布权，也不能跳过 action、checker 或最终 oracle。锚点：`plans/i18n-codex-mdx-fallback/agent/实验契约.json` 的 `comparison_arms`/`required_order`，以及 `plans/i18n-codex-mdx-fallback/agent/evidence/prettier-mdx-probe-2026-09-01.md`、`mdx-formatter-probe-2026-09-01.md`、`parallel-agent-review-2026-09-01.md`。

## 6. 日志与 artifact 事件契约

每个 fixture 至少产生一条结构化记录；每个阶段可追加事件但不得改变 attempt 语义。字段名称与 STORY-01 `experiment-schema.json`、`fixture-manifest.json.expected_log_fields` 对齐：

```json
{
  "event": "diagnostic|action_attempt|checker_result|final_outcome",
  "fixture_id": "real-27629404260-zhcn-plugin-html-comment",
  "run_id": "27629404260",
  "locale": "zh-CN",
  "source_path": "plugins-reference/anthropic-vertex.md",
  "source_revision": "66585786970c...",
  "experiment_arm": "enhanced_existing_codex_action",
  "arm": "enhanced_existing_codex_action",
  "agent_action_version": "...",
  "optional_aid": "none",
  "auxiliary_version": null,
  "repair_stage_order": ["parser", "auxiliary", "codex", "checker", "scope", "protected_attribute", "recheck", "artifact"],
  "parser": "@mdx-js/mdx@3.1.1",
  "parser_outcome": "compile_failure",
  "parser_diagnostics": [{"source": "micromark-extension-mdx-jsx", "line": 29, "column": 2, "offset": 641}],
  "error": {"source": "micromark-extension-mdx-jsx", "error_line": 29, "error_column": 2},
  "codex_session": "...",
  "attempt": 1,
  "repair_attempts": 1,
  "rounds": 1,
  "checker_result": "not_run|pass|fail",
  "content_check": "not_applicable_before_repair|pass|fail|not_run",
  "changed_paths": [],
  "elapsed_ms": 0,
  "duration_ms": 0,
  "exit_code": 0,
  "final_outcome": "success|checker_intercepted|final_failure|not_run",
  "status": "success|checker_intercepted|final_failure|not_run"
}
```

`opening_tag_line` 仅在错配 closing tag fixture（taxonomy line 975）出现时记录；`error_line/error_column` 与 `error` 对象内值必须一致。成功率定义固定为 parser compile success 且 content_check pass；checker_intercepted 单独计数，`not_run` 排除分母。artifact 至少包含 changed/deleted 清单、payload、metadata 和失败原因；单 shard 失败不得丢弃同 shard 已成功页面的证据。

## 7. 统一接入边界、停止条件与指标

本地驱动只负责准备 fixture/manifest、注入配置并调用入口；CI 子流水线只负责 runner 权限、artifact 上传和 finalizer 编排；生产接入必须等待 STORY-03.1 的用户决策（辅助去留、具体参数、灰度/时机），不能由本契约推断授权。三者使用同一输入/输出和日志 schema。

停止条件：原始快照或诊断丢失、整篇删除未被 checker 拦截、辅助或 action 绕过 parser/scope/protected gate、session 超时/尝试上限达到、路径越界、候选无法回退，或发现需要新增 Agent 入口时立即停止并转交。

评估至少记录：parser 通过率、修复成功率、灾难性删除拦截率、允许小差异误拦截率、各辅助增量成功率、反馈轮次/冲突率、单文件耗时、Codex 轮次与 token 成本、人工介入率、同 shard 成功页面保留率。历史 artifact 逐 shard 映射、硬超时/最大尝试的具体数值、辅助最终去留均保持未决，不在本 Story 定值。

## 8. STORY-01 fixture 入口映射

机器可读映射见同目录 `fixture-map.json`；该表将每个入口（启动、修复、检查、反馈、转交）逐项落到两个真实 fixture 与四个 fail-closed 类别，并保留证据路径。
