import { spawn } from "node:child_process";
import { randomUUID } from "node:crypto";

export function mockRepair({ source, failureClass, variant }) {
  if (variant === "taxonomy-delete-accordion") {
    const marker = "  <Accordion title=\"安全、凭证、配对和密钥 - M3 Beta - 6 个领域\">";
    const at = source.indexOf(marker); return at >= 0 ? source.slice(0, at) + "\n" : source.slice(0, Math.floor(source.length / 2));
  }
  if (variant === "anthropic-empty-frontmatter") return source.match(/^---\n[\s\S]*?\n---\n?/)?.[0] ?? "---\n---\n";
  if (failureClass === "mdx_syntax_html_comment") return source.replace("<!-- openclaw-plugin-reference:manual-start -->", "{/* openclaw-plugin-reference:manual-start */}").replace("<!-- openclaw-plugin-reference:manual-end -->", "{/* openclaw-plugin-reference:manual-end */}");
  if (failureClass === "mdx_syntax_mismatched_closing_tag") {
    const duplicateLabel = '<span className="maturity-score-label"><span className="maturity-score-label">';
    if (source.includes(duplicateLabel)) return source.replace(duplicateLabel, '<span className="maturity-score-label">');
    const lines = source.split("\n");
    const index = lines.findIndex((line, i) => i === 1074 && line.trim() === "</div>");
    if (index >= 0) lines.splice(index, 1);
    return lines.join("\n");
  }
  return source;
}

export async function runRealCodex({ file, prompt, timeoutMs, scratchDir, model, reasoningEffort, codexHome }) {
  const started = Date.now();
  const codex = process.env.CODEX_BIN || "/root/.nvm/versions/node/v24.15.0/bin/codex";
  const args = ["exec", "--json", "--ephemeral", "--ignore-user-config", "--sandbox", "workspace-write", "-m", model, "-c", `model_reasoning_effort=${reasoningEffort}`, "-C", scratchDir, prompt];
  return await new Promise((resolve) => {
    let stdout = "", stderr = "", timedOut = false;
    const child = spawn(codex, args, { cwd: scratchDir, env: { ...process.env, CODEX_HOME: codexHome || process.env.CODEX_HOME || "/root/.codex-profiles/personal" }, stdio: ["ignore", "pipe", "pipe"], detached: true });
    const timer = setTimeout(() => { timedOut = true; try { process.kill(-child.pid, "SIGKILL"); } catch { child.kill("SIGKILL"); } }, timeoutMs);
    child.stdout.on("data", (chunk) => { stdout += chunk; }); child.stderr.on("data", (chunk) => { stderr += chunk; });
    child.on("close", (code, signal) => { clearTimeout(timer); resolve({ session: randomUUID(), exitCode: timedOut ? 124 : (code ?? 1), signal, timedOut, stdout, stderr, durationMs: Date.now() - started, file, model, reasoningEffort }); });
    child.on("error", (error) => { clearTimeout(timer); resolve({ session: randomUUID(), exitCode: 127, error: error.message, stdout, stderr, durationMs: Date.now() - started, file }); });
  });
}
