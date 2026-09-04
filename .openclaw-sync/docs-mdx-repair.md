# OpenClaw Docs MDX Repair Agent

You are repairing generated OpenClaw documentation after a fast MDX validation failure.

Goal: repair complete pages, following the multi-round relay protocol. Each round
feeds back the current diagnostics file (`.openclaw-sync/mdx/${LOCALE}.json`); fix
all parser/checker diagnostics reported for this round. If earlier rounds already
fixed part of the errors, continue fixing the remaining diagnostics — including
errors newly surfaced by earlier repairs — until the pages pass strict MDX
compilation. The relay is bounded: rounds and per-round time are set by the
workflow (`MDX_REPAIR_MAX_ATTEMPTS`, `MDX_REPAIR_HARD_TIMEOUT_MS`), so never
invent extra retry budgets.

Hard limits:

- Edit only existing Markdown/MDX files under the locale path named by `LOCALE`.
- Do not edit source English docs unless `LOCALE=en`.
- Do not edit code, workflows, package metadata, generated sync metadata, translation memory, or assets.
- Do not add, delete, or rename files.
- Preserve the meaning of translated prose.
- Preserve all must_preserve content: frontmatter, `x-i18n.source_hash`, links, code fences, JSX component names, and existing page structure.
- Do not rewrite the whole page; keep each fix inside the diagnosed edit span or its smallest necessary paired token.
- Avoid broad formatting or retranslation.

Required workflow:

1. Read `.openclaw-sync/mdx/${LOCALE}.json` — it always carries the diagnostics for the current relay round.
2. Inspect only the listed files as complete pages (not isolated chunks) and the lines near each diagnostic.
3. Fix every diagnostic reported for this round, such as broken JSX attribute quoting, mismatched component closing tags, raw `<` text, raw HTML comments, or accidental top-level `import`/`export` text. An error newly reported in this round's feedback is in scope.
4. Run `node source/scripts/check-docs-mdx.mjs "docs/${LOCALE}" --json-out ".openclaw-sync/mdx/${LOCALE}.json"`.
5. Leave no changes outside `docs/${LOCALE}`.

When uncertain, prefer the smallest escaping fix: backticks for literal words, `&lt;` for literal `<`, double quotes around JSX attribute values, and balanced component tags. If a diagnostic cannot be fixed without guessing (for example an undeterminable broken `{...}` expression), leave that span untouched and say so in your final message rather than masking it.
