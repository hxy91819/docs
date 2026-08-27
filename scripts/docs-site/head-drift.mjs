// Classify only whether drift can change the built artifact or deployed worker.
// The workflow verifies run existence against the Actions API, never paths.
import fs from "node:fs";
import { fileURLToPath } from "node:url";

// Must mirror r2-pages.yml on.push.paths; head-drift.test.mjs asserts the sync.
export const pushTriggerPaths = [
  "docs/**",
  "scripts/docs-site/**",
  "workers/**",
  "wrangler.toml",
  "package.json",
  "package-lock.json",
  ".github/workflows/r2-pages.yml",
  ".openclaw-sync/source.json",
];

const artifactIrrelevantPaths = [
  "AGENTS.md",
  "CLAUDE.md",
  "CLOUDFLARE.md",
  "LICENSE",
  "README.md",
  "SECURITY.md",
  "Makefile",
  "skills-lock.json",
  ".agents/**",
  ".github/**",
  ".openclaw-sync/**",
];

function matchesGlob(path, glob) {
  return glob.endsWith("/**") ? path.startsWith(glob.slice(0, -2)) : path === glob;
}

export function classifyHeadDrift(changedPaths) {
  const paths = changedPaths.filter((path) => path !== "");
  if (paths.some((path) => pushTriggerPaths.some((glob) => matchesGlob(path, glob)))) {
    return "artifact-affected";
  }
  if (paths.every((path) => artifactIrrelevantPaths.some((glob) => matchesGlob(path, glob)))) {
    return "artifact-unaffected";
  }
  return "artifact-affected";
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  process.stdout.write(`${classifyHeadDrift(fs.readFileSync(0, "utf8").split("\n"))}\n`);
}
