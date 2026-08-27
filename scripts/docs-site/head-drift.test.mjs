import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { parse } from "yaml";
import { classifyHeadDrift, pushTriggerPaths } from "./head-drift.mjs";

const script = fileURLToPath(new URL("./head-drift.mjs", import.meta.url));

test("push trigger paths stay in sync with the R2 Pages workflow", () => {
  const workflow = new URL("../../.github/workflows/r2-pages.yml", import.meta.url);
  const doc = parse(fs.readFileSync(workflow, "utf8"));
  assert.deepEqual(pushTriggerPaths, (doc.on ?? doc[true]).push.paths);
});

const cases = [
  [[".openclaw-sync/source.json"], "artifact-affected"],
  [["docs/start/why-openclaw.md"], "artifact-affected"],
  [["README.md", "docs/a.md"], "artifact-affected"],
  [["README.md"], "artifact-unaffected"],
  [[".github/workflows/translate-all.yml"], "artifact-unaffected"],
  [[".openclaw-sync/check-docs-mdx.mjs"], "artifact-unaffected"],
  [[".github/workflows/r2-pages.yml"], "artifact-affected"],
  [["some-new-root-file.txt"], "artifact-affected"],
  [["README.md", "some-new-root-file.txt"], "artifact-affected"],
  [[], "artifact-unaffected"],
  [[""], "artifact-unaffected"],
  [["", "docs/a.md", ""], "artifact-affected"],
  [["some-new-root-file.txt", "docs/a.md"], "artifact-affected"],
  [["docs-extra/a.md"], "artifact-affected"],
  [[".github-extra/workflow.yml"], "artifact-affected"],
  [["README.md.bak"], "artifact-affected"],
];

for (const [paths, verdict] of cases) {
  test(`classifies ${JSON.stringify(paths)} as ${verdict}`, () => {
    assert.equal(classifyHeadDrift(paths), verdict);
  });
}

for (const [input, verdict] of [
  ["README.md\n", "artifact-unaffected"],
  [".openclaw-sync/source.json\n", "artifact-affected"],
  ["weird.txt\n", "artifact-affected"],
]) {
  test(`CLI prints ${verdict} with a trailing newline`, () => {
    assert.equal(execFileSync(process.execPath, [script], { encoding: "utf8", input }), `${verdict}\n`);
  });
}
