# 历史树扫描与重复性

## 输入与命令

历史翻译提交 `fe5cb011ff0996b6bf007ba1e8f26377f10e541a` 已在临时目录解包（不修改仓库文档）：

```text
git archive fe5cb011ff0996b6bf007ba1e8f26377f10e541a docs/zh-CN | tar -x -C .local/story01-scratch/historical-fe5
node .local/story01-scratch/scan-historical.mjs .local/story01-scratch/historical-fe5/docs/zh-CN
```

环境：Node `v24.15.0`，`@mdx-js/mdx@3.1.1`，扫描器调用 `compile(source, {jsx:true})`。

## 结果

首次与重复扫描均为退出码 `0`（扫描器本身将 parser 失败作为数据输出）：`scanned=696`、`failures=6`，两次 NDJSON `cmp` 退出码 `0`。失败明细：

```text
maturity/taxonomy.md:1075:5  Unexpected closing tag </div>, expected corresponding closing tag for <Accordion> (975:3-975:43)
plugins/reference/anthropic-vertex.md:29:2  Unexpected character ! before name (HTML comment)
plugins/reference/codex-supervisor.md:29:2  Unexpected character ! before name (HTML comment)
plugins/reference/diffs-language-pack.md:29:2  Unexpected character ! before name (HTML comment)
plugins/reference/microsoft-foundry.md:29:2  Unexpected character ! before name (HTML comment)
plugins/reference/policy.md:29:2  Unexpected character ! before name (HTML comment)
```

扫描器输出的是严格 parser 观察，不声称这些页面与 metadata-only artifact 有逐页映射；映射缺失是历史 artifact 的已知限制。
