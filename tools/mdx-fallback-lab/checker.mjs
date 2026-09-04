import crypto from "node:crypto";

export const REQUIRED_THRESHOLDS = [
  "min_retention_ratio",
  "max_deleted_run_lines",
  "max_tail_deletion_ratio",
  "max_bulk_deletion_ratio",
];

export function sha256(text) {
  return crypto.createHash("sha256").update(text).digest("hex");
}

function validateThresholds(thresholds) {
  if (!thresholds || typeof thresholds !== "object") return "checker_config_missing";
  for (const key of REQUIRED_THRESHOLDS) {
    const value = thresholds[key];
    if (typeof value !== "number" || !Number.isFinite(value) || value <= 0) return `invalid_threshold:${key}`;
  }
  if (thresholds.min_retention_ratio > 1 || thresholds.max_tail_deletion_ratio > 1 || thresholds.max_bulk_deletion_ratio > 1) {
    return "ratio_threshold_out_of_range";
  }
  if (!Number.isInteger(thresholds.max_deleted_run_lines)) return "invalid_threshold:max_deleted_run_lines";
  return null;
}

function frontmatterAndBody(text) {
  const match = text.match(/^---\n[\s\S]*?\n---\n?/);
  return { frontmatter: match?.[0] ?? "", body: match ? text.slice(match[0].length) : text };
}

// A line-level LCS gives a conservative estimate of retained content. It intentionally
// ignores wording/semantic quality and only detects catastrophic contiguous deletion.
function deletionRuns(beforeLines, afterLines) {
  const n = beforeLines.length, m = afterLines.length;
  const dp = Array.from({ length: n + 1 }, () => new Uint32Array(m + 1));
  for (let i = n - 1; i >= 0; i--) for (let j = m - 1; j >= 0; j--) {
    dp[i][j] = beforeLines[i] === afterLines[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
  }
  const kept = new Set(); let i = 0, j = 0;
  while (i < n && j < m) {
    if (beforeLines[i] === afterLines[j]) { kept.add(i); i++; j++; }
    else if (dp[i + 1][j] >= dp[i][j + 1]) i++;
    else j++;
  }
  const runs = []; let start = null;
  for (let k = 0; k < n; k++) {
    if (!kept.has(k) && start === null) start = k;
    if ((kept.has(k) || k === n - 1) && start !== null) {
      const end = kept.has(k) ? k - 1 : k;
      runs.push({ start, end, lines: end - start + 1 }); start = null;
    }
  }
  return { keptLines: kept.size, runs };
}

export function checkContent(before, after, thresholds) {
  const beforeHash = sha256(before); const afterHash = sha256(after ?? "");
  const configError = validateThresholds(thresholds);
  const base = { result: "fail", violations: [], thresholds: thresholds ?? null, before_sha256: beforeHash, after_sha256: afterHash };
  if (configError) { base.violations.push({ code: configError, detail: "checker thresholds are required and fail closed" }); return base; }
  if (typeof after !== "string" || after.length === 0) { base.violations.push({ code: "empty_output", detail: "output is missing or zero bytes" }); return base; }
  const beforeParts = frontmatterAndBody(before), afterParts = frontmatterAndBody(after);
  if (beforeParts.body.trim() && !afterParts.body.trim()) { base.violations.push({ code: "empty_output", detail: "only empty frontmatter remains" }); return base; }
  const beforeLines = before.split(/\n/), afterLines = after.split(/\n/);
  const { keptLines, runs } = deletionRuns(beforeLines, afterLines);
  const retention = beforeLines.length ? keptLines / beforeLines.length : 1;
  const deleted = beforeLines.length - keptLines;
  const longest = runs.reduce((max, run) => Math.max(max, run.lines), 0);
  const tailRun = runs.find((run) => run.end === beforeLines.length - 1);
  const tailRatio = tailRun ? tailRun.lines / beforeLines.length : 0;
  if (retention < thresholds.min_retention_ratio) base.violations.push({ code: "whole_document_deleted", detail: `retention ${retention.toFixed(4)} below ${thresholds.min_retention_ratio}` });
  if (longest > thresholds.max_deleted_run_lines) base.violations.push({ code: "abrupt_truncation", detail: `deleted run ${longest} lines exceeds ${thresholds.max_deleted_run_lines}` });
  if (tailRatio > thresholds.max_tail_deletion_ratio) base.violations.push({ code: "abrupt_truncation", detail: `tail deletion ratio ${tailRatio.toFixed(4)} exceeds ${thresholds.max_tail_deletion_ratio}` });
  if (beforeLines.length && deleted / beforeLines.length > thresholds.max_bulk_deletion_ratio) base.violations.push({ code: "abrupt_bulk_deletion", detail: `deleted ratio ${(deleted / beforeLines.length).toFixed(4)} exceeds ${thresholds.max_bulk_deletion_ratio}` });
  base.metrics = { before_lines: beforeLines.length, after_lines: afterLines.length, retained_lines: keptLines, retention_ratio: retention, deleted_lines: deleted, longest_deleted_run_lines: longest, tail_deletion_ratio: tailRatio };
  base.result = base.violations.length ? "fail" : "pass";
  return base;
}
