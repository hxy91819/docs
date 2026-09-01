# MDX 专用 formatter 初步探测

日期：2026-09-01

## 目的

确认一个比 Prettier 更接近 MDX 的 formatter，是否能够把当前 fallback
遇到的损坏输入直接恢复为可编译 MDX。这个探测只用于候选筛选，不代表生产
接入决定。

## 环境与输入

- 包：`@takazudo/mdx-formatter@1.3.0-next.4`
- 调用：`format(input)`，在临时目录安装，不修改仓库依赖
- 输入：五个最小合成样例，分别覆盖伪造标签、未闭合真实元素、游离闭标签、
  unquoted 属性值和 HTML 注释

另外对 `@markdownkit/markdownkit@2.3.2` 执行了一次 CLI `format` 混合样例探测，
同样在 HTML 注释处解析失败，退出码为 1，报告 `Formatted 0 of 1 files`，原文件
未改变。这个单样例结果不能代表该项目全部规则，只能说明它目前没有显露出可直接
恢复本故障的行为。

## 结果

| 样例 | formatter 输出 | 结论 |
| --- | --- | --- |
| `文本 <id>保留` | 原样返回 | 未删除伪造标签 |
| `<div>` 后缺 `</div>` | 原样返回 | 未补闭合标签 |
| `</span>` 与外层元素错配 | 原样返回 | 未删除游离闭标签 |
| `<Card title=Domande />` | 原样返回 | 未给属性值加引号 |
| `<!-- 注释 -->` | 原样返回 | 未转换为 MDX 注释 |

`@takazudo/mdx-formatter` 的五个样例均为 `changed: false`，没有一个从损坏状态
变成修复状态。
这与该项目文档所述的行为一致：formatter 先解析 MDX，解析失败时返回原文，
而不是猜测修复。它仍可能适合格式化已经合法的 MDX，但不能替代严格 parser
或 Codex repair action。

## 决策影响

1. `@takazudo/mdx-formatter` 不进入本轮主实验臂，也不加入仓库默认依赖。
2. 若真实流水线 fixture 暴露“语法已经合法、仅格式漂移”的独立收益，可在临时
   副本上以固定版本重新测量；输出必须经过严格 MDX、轻量内容和受保护属性门禁。
3. 当前仍以增强现有 Codex action 处理损坏输入；不因发现一个 MDX formatter
   就扩大候选组合矩阵。

这是合成输入的初筛，不能替代真实流水线 fixture 的复验。

参考：[项目仓库](https://github.com/Takazudo/mdx-formatter)、[API 行为说明](https://mdx-formatter.takazudomodular.com/v/0x/docs/overview/api/)、[解析失败处理说明](https://mdx-formatter.takazudomodular.com/docs/formatting/)。
