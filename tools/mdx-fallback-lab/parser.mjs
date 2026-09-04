import { compile } from "@mdx-js/mdx";

export const PARSER = "@mdx-js/mdx@3.1.1 compile({jsx:true})";

export async function parseMdx(source) {
  try { await compile(source, { jsx: true }); return { outcome: "compile_success", diagnostics: [], error: null }; }
  catch (error) {
    const point = error?.place?.start ?? error?.place ?? error ?? {};
    const sourceName = error?.source ?? error?.name ?? "mdx";
    const diagnostic = { source: sourceName, line: point.line ?? null, column: point.column ?? null, offset: point.offset ?? null };
    return { outcome: "compile_failure", diagnostics: [diagnostic], error: { source: sourceName, reason: error?.reason ?? String(error?.message ?? error), error_line: diagnostic.line, error_column: diagnostic.column } };
  }
}
