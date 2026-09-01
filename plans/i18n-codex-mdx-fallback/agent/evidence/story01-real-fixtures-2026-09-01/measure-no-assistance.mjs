import { readFileSync } from "node:fs";
import { performance } from "node:perf_hooks";
import { compile } from "@mdx-js/mdx";

const files = process.argv.slice(2);
if (!files.length) {
  console.error("usage: node measure-no-assistance.mjs <fixture> [...fixture]");
  process.exit(2);
}
for (const file of files) {
  const source = readFileSync(file, "utf8");
  const started = performance.now();
  let parserOutcome = "compile_success";
  let error;
  try {
    await compile(source, { jsx: true });
  } catch (caught) {
    parserOutcome = "compile_failure";
    error = {
      source: caught.source ?? null,
      reason: caught.reason ?? String(caught.message ?? caught).split("\n")[0],
      line: caught.line ?? caught.place?.start?.line ?? null,
      column: caught.column ?? caught.place?.start?.column ?? null,
    };
  }
  const durationMs = Math.round((performance.now() - started) * 100) / 100;
  console.log(JSON.stringify({
    fixture_id: file,
    run_id: "27629404260",
    locale: "zh-CN",
    source_path: file,
    arm: "no_assistance",
    repair_mode: "none",
    auxiliary_version: null,
    parser: "@mdx-js/mdx@3.1.1",
    parser_outcome: parserOutcome,
    error: error ?? null,
    content_check: "not_applicable_before_repair",
    repair_attempts: 0,
    rounds: 0,
    duration_ms: durationMs,
    exit_code: parserOutcome === "compile_failure" ? 1 : 0,
    status: parserOutcome === "compile_failure" ? "final_failure" : "success",
  }));
}
