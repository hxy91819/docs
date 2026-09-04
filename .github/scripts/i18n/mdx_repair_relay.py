#!/usr/bin/env python3
"""Drive the bounded Codex MDX repair relay for one locale shard.

Definition:
  Control plane for the existing "Repair translated MDX" step
  (openai/codex-action@v1, prompt contract .openclaw-sync/docs-mdx-repair.md).
  Implements the D-09 multi-round relay protocol from
  plans/i18n-codex-mdx-fallback: the single repair action runs on complete
  pages, is fed the current strict diagnostics before every round, and is
  bounded by MDX_REPAIR_MAX_ATTEMPTS rounds with MDX_REPAIR_HARD_TIMEOUT_MS
  per round. There is no second Agent entry and no auxiliary arm.

  decide freezes the contract startup conditions (contract §1): the relay
  starts only when the strict MDX check failed, the pending manifest is
  non-empty, compile diagnostics with file/line/column exist, and every
  diagnostic stays inside docs/<locale>. Otherwise it records not_run.
  decide also snapshots locale page hashes so the report can detect
  repair-phase page deletion or emptying (contract §3 empty_output and
  whole_document_deleted; threshold-free, so no checker config is required).

  report classifies the relay outcome (success, partial_success,
  final_failure, not_run), keeps per-round diagnostics history, and records
  per-page failures with top-level error_source/error_line/error_column plus
  repair_mode, rounds, and changed/deleted paths for artifact metadata.

Parameters:
  command: decide or report.
  --workspace: Git workspace root. Default: GITHUB_WORKSPACE or current dir.

Environment:
  LOCALE, LOCALE_SLUG, SHARD_INDEX, SHARD_TOTAL, MDX_CHECK_OUTCOME.
  MDX_REPAIR_MAX_ATTEMPTS (default 4), MDX_REPAIR_HARD_TIMEOUT_MS (default
  600000) must be positive integers; MDX_REPAIR_AUXILIARY_MODE (default
  none) must be none because auxiliary arms are not enabled in production.
  report also reads MDX_REPAIR_ROUNDS_OUTCOMES (12 outcome tokens, three per
  relay round: action scope recheck).

Outputs:
  decide writes .openclaw-sync/mdx/<locale>-repair-state.json and the
  pre-repair content snapshot, and GITHUB_OUTPUT decision/reason.
  report writes .openclaw-sync/mdx/<locale>-repair-report.json and
  GITHUB_OUTPUT final_outcome/failure_kind/repair_mode/rounds/recheck_outcome/
  failed_paths/nonsyntax_failed_paths/changed_paths/failed_count/changed_count.
  Both commands print the structured record to stdout.

Examples:
  LOCALE=fr LOCALE_SLUG=fr SHARD_INDEX=0 SHARD_TOTAL=1 MDX_CHECK_OUTCOME=failure python .github/scripts/i18n/mdx_repair_relay.py decide
  LOCALE=fr LOCALE_SLUG=fr SHARD_INDEX=0 SHARD_TOTAL=1 MDX_CHECK_OUTCOME=failure MDX_REPAIR_ROUNDS_OUTCOMES="success success failure skipped skipped skipped skipped skipped skipped skipped skipped skipped" python .github/scripts/i18n/mdx_repair_relay.py report
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path

DEFAULT_MAX_ATTEMPTS = "4"
DEFAULT_HARD_TIMEOUT_MS = "600000"
MESSAGE_LIMIT = 300
POSITIVE_INT_RE = re.compile(r"^[1-9][0-9]*$")


def workspace_path(raw: str | None) -> Path:
    return Path(raw).resolve() if raw else Path.cwd()


def parse_positive_int(name: str) -> int:
    raw = (os.environ.get(name) or "").strip() or {"MDX_REPAIR_MAX_ATTEMPTS": DEFAULT_MAX_ATTEMPTS, "MDX_REPAIR_HARD_TIMEOUT_MS": DEFAULT_HARD_TIMEOUT_MS}[name]
    if not POSITIVE_INT_RE.fullmatch(raw):
        raise SystemExit(f"invalid {name}: {raw!r}; relay budgets must be positive integers (no unbounded retry)")
    return int(raw)


def relay_auxiliary_mode() -> str:
    raw = (os.environ.get("MDX_REPAIR_AUXILIARY_MODE") or "none").strip().lower()
    if raw != "none":
        raise SystemExit(
            f"MDX_REPAIR_AUXILIARY_MODE={raw!r} is not enabled in production; "
            "the relay runs the single Codex action without auxiliary arms (fail-closed)"
        )
    return raw


def relay_config() -> dict[str, object]:
    return {
        "max_attempts": parse_positive_int("MDX_REPAIR_MAX_ATTEMPTS"),
        "hard_timeout_ms": parse_positive_int("MDX_REPAIR_HARD_TIMEOUT_MS"),
        "auxiliary_mode": relay_auxiliary_mode(),
    }


def mdx_dir(workspace: Path) -> Path:
    return workspace / ".openclaw-sync" / "mdx"


def write_outputs(mapping: dict[str, object]) -> None:
    output = os.environ.get("GITHUB_OUTPUT")
    if not output:
        return
    with Path(output).open("a", encoding="utf-8") as fh:
        for key, value in mapping.items():
            fh.write(f"{key}={value}\n")


def read_manifest_sources(workspace: Path, locale_slug: str, shard_index: str, shard_total: str) -> list[Path]:
    manifest = workspace / ".openclaw-sync" / f"docs-i18n-{locale_slug}-s{shard_index}of{shard_total}.txt"
    if not manifest.is_file():
        return []
    return [Path(line.strip()) for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_diagnostics(path: Path) -> list[dict] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    errors = payload.get("errors") if isinstance(payload, dict) else None
    if not isinstance(errors, list):
        return None
    return [error for error in errors if isinstance(error, dict)]


def locale_page_path(locale: str, source: Path, docs_root: Path) -> str | None:
    try:
        rel = source.resolve().relative_to(docs_root).as_posix()
    except (ValueError, OSError):
        return None
    if not rel.endswith((".md", ".mdx")):
        return None
    return f"docs/{locale}/{rel}"


def content_snapshot(workspace: Path, locale: str) -> dict[str, str]:
    root = workspace / "docs" / locale
    snapshot: dict[str, str] = {}
    if not root.is_dir():
        return snapshot
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix in {".md", ".mdx"}:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            snapshot[path.relative_to(workspace).as_posix()] = digest
    return snapshot


def snapshot_path(workspace: Path, locale: str) -> Path:
    base = os.environ.get("RUNNER_TEMP") or ""
    root = Path(base) if base else mdx_dir(workspace)
    return root / f"{locale}.repair-content-snapshot.json"


def is_empty_page(path: Path) -> bool:
    try:
        return not path.read_text(encoding="utf-8", errors="ignore").strip()
    except OSError:
        return False


def trunc(message: object) -> str:
    text = str(message or "").split("\n")[0]
    return text[:MESSAGE_LIMIT]


def decide(workspace: Path) -> None:
    locale = os.environ["LOCALE"]
    locale_slug = os.environ["LOCALE_SLUG"]
    shard_index = os.environ["SHARD_INDEX"]
    shard_total = os.environ["SHARD_TOTAL"]
    config = relay_config()
    check_outcome = os.environ.get("MDX_CHECK_OUTCOME", "skipped")

    sources = read_manifest_sources(workspace, locale_slug, shard_index, shard_total)
    diagnostics_path = mdx_dir(workspace) / f"{locale}.json"
    errors = read_diagnostics(diagnostics_path) if check_outcome == "failure" else []
    docs_root = (workspace / "docs").resolve()
    decision = "run"
    reason = ""
    if check_outcome != "failure":
        decision, reason = "not_run", f"mdx_check_{check_outcome or 'skipped'}"
    elif not sources:
        decision, reason = "not_run", "no_pending_files"
    elif errors is None:
        decision, reason = "not_run", "diagnostics_unavailable"
    elif not [error for error in errors if error.get("type") == "mdx"]:
        decision, reason = "not_run", "no_mdx_compile_diagnostics"
    elif any(not str(error.get("file", "")).startswith(f"docs/{locale}/") for error in errors):
        decision, reason = "not_run", "diagnostics_out_of_locale_scope"

    state = {
        "decision": decision,
        "not_run_reason": reason,
        "locale": locale,
        "locale_slug": locale_slug,
        "shard_index": shard_index,
        "shard_total": shard_total,
        "mdx_check_outcome": check_outcome,
        "repair_mode": "relay" if decision == "run" else "none",
        **config,
    }
    mdx_dir(workspace).mkdir(parents=True, exist_ok=True)
    state_path = mdx_dir(workspace) / f"{locale}-repair-state.json"
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if decision == "run":
        snapshot = content_snapshot(workspace, locale)
        snapshot_file = snapshot_path(workspace, locale)
        snapshot_file.parent.mkdir(parents=True, exist_ok=True)
        snapshot_file.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_outputs({"decision": decision, "reason": reason})
    print(json.dumps(state, sort_keys=True))


def round_history(workspace: Path, locale: str, max_attempts: int) -> list[dict[str, object]]:
    history: list[dict[str, object]] = []
    for round_index in range(1, max_attempts + 1):
        path = mdx_dir(workspace) / f"{locale}-round-{round_index}.json"
        errors = read_diagnostics(path)
        if errors is None:
            continue
        entry: dict[str, object] = {"round": round_index, "error_count": len(errors)}
        if errors:
            first = errors[0]
            entry["first_error"] = {
                "file": first.get("file", ""),
                "type": first.get("type", ""),
                "line": first.get("line"),
                "column": first.get("column"),
                "message": trunc(first.get("message")),
            }
        history.append(entry)
    return history


def parse_round_outcomes() -> list[list[str]]:
    raw = os.environ.get("MDX_REPAIR_ROUNDS_OUTCOMES", "")
    tokens = raw.split()
    tokens += ["skipped"] * (12 - len(tokens))
    return [tokens[index : index + 3] for index in range(0, 12, 3)]


def classify_report(
    state: dict[str, object],
    errors: list[dict],
    rounds_outcomes: list[list[str]],
    workspace: Path,
    locale: str,
) -> dict[str, object]:
    decision = str(state.get("decision", "not_run"))
    rounds = sum(1 for action, _scope, _recheck in rounds_outcomes if action not in {"skipped", ""})
    if decision != "run":
        # The relay state is authoritative: without a run decision no repair
        # round executed, regardless of any outcome tokens.
        rounds = 0
    executed = [round for round in rounds_outcomes[:rounds]]
    recheck_outcome = executed[-1][2] if executed else "skipped"

    failed_records: dict[str, dict[str, object]] = {}
    nonsyntax: list[str] = []
    for error in errors:
        path = str(error.get("file", ""))
        if not path.startswith(f"docs/{locale}/") or path in failed_records:
            continue
        failed_records[path] = {
            "path": path,
            "error_source": error.get("type", ""),
            "error_line": error.get("line"),
            "error_column": error.get("column"),
            "message": trunc(error.get("message")),
        }
        if error.get("type") != "mdx":
            nonsyntax.append(path)

    snapshot_file = snapshot_path(workspace, locale)
    before: dict[str, str] = {}
    if snapshot_file.is_file():
        try:
            loaded = json.loads(snapshot_file.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                before = {str(key): str(value) for key, value in loaded.items()}
        except (OSError, json.JSONDecodeError):
            before = {}
    current = content_snapshot(workspace, locale)
    changed_paths = [
        {"path": path, "before_sha256": before.get(path), "after_sha256": digest}
        for path, digest in sorted(current.items())
        if before.get(path) != digest
    ]
    deleted_paths = sorted(path for path in before if path not in current)
    emptied_paths = sorted(
        path
        for path in sorted(set(before) & set(current))
        if before[path] != current[path] and is_empty_page(workspace / path)
    )
    violations = (
        [{"gate": "checker", "code": "whole_document_deleted", "path": path} for path in deleted_paths]
        + [{"gate": "checker", "code": "empty_output", "path": path} for path in emptied_paths]
    )

    any_action_failed = any(action == "failure" for action, _scope, _recheck in executed)
    any_scope_failed = any(scope == "failure" for _action, scope, _recheck in executed)
    if violations:
        # Repair-phase page deletion or emptying is a content-loss violation
        # (contract §3 empty_output / whole_document_deleted); it can never
        # count as a successful repair even when the parser is satisfied.
        failure_kind = "content_loss"
    elif any_action_failed:
        failure_kind = "action_failed"
    elif any_scope_failed:
        failure_kind = "scope_failed"
    elif rounds == 0:
        failure_kind = "action_failed" if decision == "run" else "none"
    elif recheck_outcome == "success":
        failure_kind = "none"
    else:
        failure_kind = "compile_failed"

    if decision != "run":
        final_outcome = "not_run"
    elif failure_kind in {"content_loss", "action_failed", "scope_failed"}:
        final_outcome = "final_failure"
    elif recheck_outcome == "success":
        final_outcome = "success"
    else:
        docs_root = (workspace / "docs").resolve()
        pending_pages = [
            page
            for page in (
                locale_page_path(locale, source, docs_root)
                for source in read_manifest_sources(
                    workspace,
                    str(state.get("locale_slug", "")),
                    str(state.get("shard_index", "")),
                    str(state.get("shard_total", "")),
                )
            )
            if page
        ]
        passing = [
            page
            for page in pending_pages
            if page not in failed_records and (workspace / page).is_file()
        ]
        final_outcome = "partial_success" if passing else "final_failure"

    first_failure = failed_records[sorted(failed_records)[0]] if failed_records else None
    return {
        "rounds": rounds,
        "repair_attempts": rounds,
        "recheck_outcome": recheck_outcome,
        "failure_kind": failure_kind,
        "final_outcome": final_outcome,
        "failed_paths": [failed_records[path] for path in sorted(failed_records)],
        "nonsyntax_failed_paths": sorted(set(nonsyntax)),
        "changed_paths": changed_paths,
        "deleted_paths": deleted_paths,
        "violations": violations,
        "first_error": first_failure,
    }


def report(workspace: Path) -> None:
    locale = os.environ["LOCALE"]
    config = relay_config()
    state_path = mdx_dir(workspace) / f"{locale}-repair-state.json"
    state: dict[str, object] = {"decision": "not_run", "not_run_reason": "state_missing"}
    if state_path.is_file():
        try:
            loaded = json.loads(state_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                state = loaded
        except json.JSONDecodeError:
            pass
    errors = read_diagnostics(mdx_dir(workspace) / f"{locale}.json") or []
    classification = classify_report(state, errors, parse_round_outcomes(), workspace, locale)

    payload: dict[str, object] = {
        "event": "final_outcome",
        "locale": locale,
        "repair_mode": state.get("repair_mode", "none"),
        "repair_stage_order": ["parser", "auxiliary", "codex", "checker", "scope", "protected_attribute", "recheck", "artifact"],
        "decision": state.get("decision", "not_run"),
        "not_run_reason": state.get("not_run_reason", ""),
        "max_attempts": config["max_attempts"],
        "hard_timeout_ms": config["hard_timeout_ms"],
        "auxiliary_mode": config["auxiliary_mode"],
        "rounds_history": round_history(workspace, locale, int(config["max_attempts"])),
        "parser_outcome": "compile_failure" if errors else "compile_success",
        "parser_diagnostics_count": len(errors),
        "error_source": None,
        "error_line": None,
        "error_column": None,
        **classification,
    }
    first_error = payload.get("first_error")
    if isinstance(first_error, dict):
        payload["error_source"] = first_error.get("error_source")
        payload["error_line"] = first_error.get("error_line")
        payload["error_column"] = first_error.get("error_column")
    payload.pop("first_error")

    report_path = mdx_dir(workspace) / f"{locale}-repair-report.json"
    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    failed_paths = [str(record["path"]) for record in payload["failed_paths"]]  # type: ignore[index,union-attr]
    changed_paths = [str(record["path"]) for record in payload["changed_paths"]]  # type: ignore[index,union-attr]
    write_outputs(
        {
            "final_outcome": str(payload["final_outcome"]),
            "failure_kind": str(payload["failure_kind"]),
            "repair_mode": str(payload["repair_mode"]),
            "rounds": str(payload["rounds"]),
            "recheck_outcome": str(payload["recheck_outcome"]),
            "failed_paths": " ".join(failed_paths),
            "nonsyntax_failed_paths": " ".join(payload["nonsyntax_failed_paths"]),  # type: ignore[arg-type]
            "changed_paths": " ".join(changed_paths),
            "failed_count": str(len(failed_paths)),
            "changed_count": str(len(changed_paths)),
        }
    )
    print(json.dumps(payload, sort_keys=True))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Decide and report the bounded Codex MDX repair relay for one locale shard.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Outputs:
  decide writes the relay state plus content snapshot and GITHUB_OUTPUT decision/reason.
  report writes the relay report JSON and GITHUB_OUTPUT outcome fields.

Examples:
  LOCALE=fr LOCALE_SLUG=fr SHARD_INDEX=0 SHARD_TOTAL=1 MDX_CHECK_OUTCOME=failure python .github/scripts/i18n/mdx_repair_relay.py decide
  LOCALE=fr LOCALE_SLUG=fr SHARD_INDEX=0 SHARD_TOTAL=1 MDX_CHECK_OUTCOME=failure MDX_REPAIR_ROUNDS_OUTCOMES="success success failure skipped skipped skipped skipped skipped skipped skipped skipped skipped" python .github/scripts/i18n/mdx_repair_relay.py report
""",
    )
    parser.add_argument("command", choices=["decide", "report"])
    parser.add_argument("--workspace", default=os.environ.get("GITHUB_WORKSPACE", "."), type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    workspace = args.workspace.resolve()
    if args.command == "decide":
        decide(workspace)
    else:
        report(workspace)


if __name__ == "__main__":
    main()
