# Prettier MDX 初步探测

## 环境

- `prettier@3.9.6`
- 仓库严格解析器：`@mdx-js/mdx@3.1.1`
- Prettier 调用：`prettier.format(input, { parser: "mdx", proseWrap: "preserve" })`
- 验收：将格式化结果交给 `createProcessor({ format: "mdx" }).parse()`

## 结果

| 变体 | Prettier 输出 | 严格 MDX 结果 |
| --- | --- | --- |
| 伪造未闭合标签 `<id>` | 基本不变 | 仍失败 |
| 真实元素丢闭合标签 | 基本不变 | 仍失败 |
| 游离闭标签 | 基本不变 | 仍失败 |
| 未加引号属性值 | 基本不变 | 仍失败 |
| 属性名位置垃圾字符 | 基本不变 | 仍失败 |
| HTML 注释 `<!-- -->` | 可能调整空行 | 仍失败（MDX 需要表达式注释） |
| 合法嵌套 MDX | 正常格式化 | 通过 |

## 结论

Prettier 可以作为合法输入的格式化器，但本次故障中的语法损坏不会被它推断修复。它不能替代严格 MDX oracle，也不能替代 Codex fallback。若继续实验，只允许对单个失败文件的临时副本使用固定版本；格式化结果必须重新通过严格解析、轻量内容检查和受保护属性检查，否则丢弃结果并回到现有 Codex action。

本记录是初步探测，不是最终的生产决策。后续仍需用真实流水线 fixture 验证是否存在 Prettier 能带来净收益的故障类别。

官方背景：[Prettier 的格式化说明](https://prettier.io/docs/index.html)、[format API](https://prettier.io/docs/api/) 和 [3.9 的 MDX parser 迁移说明](https://prettier.io/blog/2026/06/27/3.9.0.html)。
