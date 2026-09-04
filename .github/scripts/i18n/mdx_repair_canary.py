#!/usr/bin/env python3
"""Canary switch, RELEASE gate, and release summary for the MDX repair relay.

Definition:
  STORY-06 control plane (plans/i18n-codex-mdx-fallback) for the staged,
  reversible rollout of the enhanced existing Codex repair relay (single
  entry: openai/codex-action@v1). The default configuration keeps the
  translation workflow byte-equivalent to the original failure path: with
  mdx_repair_enabled=false every relay step is skipped and nothing new runs.

  decide evaluates the canary scope for one locale shard, fail-closed. The
  relay only starts when the master switch is on, the locale is an exact
  member of the canary_locales whitelist (comma-separated; the workflow
  gate expression expects no spaces, e.g. zh-CN,ja-JP), every pending page
  sits inside the
  canary_paths whitelist (locale-relative file paths or directory prefixes),
  and the mdx-repair-gate job (the mdx-repair-validation.yml sub-pipeline
  reused via workflow_call, artifacts mdx-repair-validation-*-<run_id>)
  finished in the same run. Every other outcome disables the relay for the
  run, which is the original failure path; decide itself only fails on an
  invalid gate policy so misconfiguration is never silently ignored.

  gate consumes the validation classification before any publication
  (RELEASE gate signal): only classification=success passes. agent_failure
  and environment_failure are recorded and then either fall back (relay
  stays disabled, original failure path) or abort the canary per
  CANARY_GATE_FAILURE_POLICY. The gate result and the downloaded
  classification evidence must agree; mismatches fail closed.

  summary renders the release notes (AC-03): repaired pages with
  repair_mode and rounds, checker intercepted pages, failed pages, and
  remaining risks, plus the R2/Pages publish integrity record. The run
  28273967200 stale-R2 lesson is encoded here: content verification is
  always explicitly verified or unverified-with-reason, never assumed.

  r2-smoke verifies after publish that the live page h1 matches the h1
  derived from the applied artifact page. Anything it cannot verify is
  recorded with an explicit reason; mismatches fail when verification is
  required.

Parameters:
  command: decide | gate | summary | r2-smoke.
  --workspace: Git workspace root. Default: GITHUB_WORKSPACE or current dir.
  gate --evidence-dir: Directory holding the downloaded
    mdx-repair-validation-real-codex-<run_id> artifact. Default:
    .openclaw-sync/mdx-repair-gate.
  summary --artifact-dir: Applied locale artifact directory with
    metadata.json and mdx-repair-report.json.
  r2-smoke --locale/--page-path: Locale and locale-relative page route of
    the canary page. --live-url: Live URL to verify. --docs-root: Applied
    docs tree. Default: docs. --timeout-seconds/--poll-seconds: Live poll
    budget. Defaults: 120/10.

Environment (decide):
  MDX_REPAIR_ENABLED_INPUT ("true"/"false"), CANARY_LOCALES, CANARY_PATHS,
  CANARY_GATE_FAILURE_POLICY (fallback|abort), MDX_REPAIR_GATE_RESULT,
  LOCALE, LOCALE_SLUG, SHARD_INDEX, SHARD_TOTAL.
Environment (gate):
  MDX_REPAIR_GATE_RESULT, CANARY_GATE_FAILURE_POLICY.
Environment (summary):
  LOCALE, LOCALE_SLUG, SHARD_INDEX, SHARD_TOTAL, ARTIFACT_ROLE,
  GATE_DECISION, GATE_CLASSIFICATION, GATE_REASON,
  CANARY_GATE_FAILURE_POLICY, R2_SMOKE_OUTCOME, R2_SMOKE_REASON,
  R2_SMOKE_EXPECTED_H1, PAGES_DISPATCH_WAITED.
Environment (r2-smoke):
  R2_SMOKE_REQUIRE_VERIFIED ("1" fails on unverified/mismatch),
  R2_SMOKE_UNVERIFIED_REASON (records unverified without fetching).

Outputs:
  decide writes .openclaw-sync/mdx/<locale>-canary-decision.json,
  GITHUB_OUTPUT enabled/reason, and GITHUB_ENV
  MDX_REPAIR_CANARY_ENABLED=true|false.
  gate writes <evidence-dir>/gate-decision.json and GITHUB_OUTPUT
  gate_decision/classification/reason; the abort policy exits non-zero
  after recording.
  summary writes
  .openclaw-sync/canary-release-summary-<slug>-s<i>of<t>.json, appends the
  release notes to GITHUB_STEP_SUMMARY, and prints the record.
  r2-smoke writes GITHUB_OUTPUT r2_smoke/r2_smoke_reason/expected_h1.

Examples:
  LOCALE=zh-CN LOCALE_SLUG=zh-CN SHARD_INDEX=0 SHARD_TOTAL=1 MDX_REPAIR_ENABLED_INPUT=true CANARY_LOCALES="zh-CN" CANARY_PATHS="channels/line.md" MDX_REPAIR_GATE_RESULT=success python .github/scripts/i18n/mdx_repair_canary.py decide
  MDX_REPAIR_GATE_RESULT=success python .github/scripts/i18n/mdx_repair_canary.py gate --evidence-dir .openclaw-sync/mdx-repair-gate
  LOCALE=zh-CN LOCALE_SLUG=zh-CN SHARD_INDEX=0 SHARD_TOTAL=1 python .github/scripts/i18n/mdx_repair_canary.py summary --artifact-dir .openclaw-sync/i18n-artifacts/zh-CN-s0of1
  LOCALE=zh-CN R2_SMOKE_REQUIRE_VERIFIED=1 python .github/scripts/i18n/mdx_repair_canary.py r2-smoke --locale zh-CN --page-path channels/line --live-url https://docs.openclaw.ai/zh-CN/channels/line
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# Reuse the live h1 extraction/fetch helpers so the publish smoke keeps one
# implementation of "what the live page says".
import dispatch_r2_pages  # noqa: E402

# Reuse the pending-manifest reader so canary scope checks the same manifest
# the relay decide step consumes.
import mdx_repair_relay  # noqa: E402

GATE_POLICIES = ("fallback", "abort")
CANARY_ENV_VAR = "MDX_REPAIR_CANARY_ENABLED"
FAILURE_CLASSES = ("agent_failure", "environment_failure")


def sanitize_reason_token(raw: object) -> str:
    token = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(raw or "").strip())
    return token[:100]


def parse_scope_list(raw: str | None) -> list[str]:
    return [token for token in (raw or "").replace(",", " ").split() if token]


def write_outputs(mapping: dict[str, str]) -> None:
    output = os.environ.get("GITHUB_OUTPUT")
    if not output:
        return
    with Path(output).open("a", encoding="utf-8") as fh:
        for key, value in mapping.items():
            fh.write(f"{key}={value}\n")


def append_env(mapping: dict[str, str]) -> None:
    env_file = os.environ.get("GITHUB_ENV")
    if not env_file:
        return
    with Path(env_file).open("a", encoding="utf-8") as fh:
        for key, value in mapping.items():
            fh.write(f"{key}={value}\n")


def read_json(path: Path) -> dict[str, object] | None:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return loaded if isinstance(loaded, dict) else None


def read_manifest_locale_pages(
    workspace: Path, locale: str, locale_slug: str, shard_index: str, shard_total: str
) -> list[str]:
    docs_root = (workspace / "docs").resolve()
    pages: list[str] = []
    for source in mdx_repair_relay.read_manifest_sources(workspace, locale_slug, shard_index, shard_total):
        try:
            rel = source.resolve().relative_to(docs_root).as_posix()
        except (ValueError, OSError):
            pages.append(f"__unresolvable__:{source}")
            continue
        pages.append(f"docs/{locale}/{rel}")
    return pages


def path_within_scope(page: str, locale: str, prefixes: list[str]) -> bool:
    prefix = f"docs/{locale}/"
    if not page.startswith(prefix):
        return False
    rel = page.removeprefix(prefix)
    for entry in prefixes:
        scoped = entry.strip("/")
        if rel == scoped or rel.startswith(f"{scoped}/"):
            return True
    return False


def decide_canary(workspace: Path) -> tuple[bool, str, dict[str, object]]:
    locale = os.environ.get("LOCALE", "")
    locale_slug = os.environ.get("LOCALE_SLUG", "") or locale
    shard_index = os.environ.get("SHARD_INDEX", "0")
    shard_total = os.environ.get("SHARD_TOTAL", "1")
    enabled_input = (os.environ.get("MDX_REPAIR_ENABLED_INPUT") or "").strip().lower()
    policy = (os.environ.get("CANARY_GATE_FAILURE_POLICY") or "fallback").strip().lower()
    gate_result = (os.environ.get("MDX_REPAIR_GATE_RESULT") or "skipped").strip().lower()
    locales = parse_scope_list(os.environ.get("CANARY_LOCALES"))
    paths = parse_scope_list(os.environ.get("CANARY_PATHS"))
    pending = read_manifest_locale_pages(workspace, locale, locale_slug, shard_index, shard_total)

    enabled = False
    reason = "switch_off"
    outside: list[str] = []
    if enabled_input != "true":
        reason = "switch_off"
    elif policy not in GATE_POLICIES:
        raise SystemExit(f"invalid CANARY_GATE_FAILURE_POLICY: {policy!r}; expected fallback or abort")
    elif not locales:
        reason = "canary_locales_empty"
    elif locale not in locales:
        reason = "locale_not_in_canary_scope"
    elif not paths:
        reason = "canary_paths_empty"
    else:
        outside = [page for page in pending if not path_within_scope(page, locale, paths)]
        if outside:
            reason = f"pending_paths_outside_canary_scope_{sanitize_reason_token(outside[0])}"
        elif gate_result == "success":
            enabled = True
            reason = "canary_enabled"
        elif gate_result == "failure":
            reason = "validation_gate_failure"
        else:
            token = sanitize_reason_token(gate_result) or "skipped"
            reason = f"validation_gate_{token}"

    state: dict[str, object] = {
        "event": "canary_decision",
        "enabled": enabled,
        "reason": reason,
        "locale": locale,
        "locale_slug": locale_slug,
        "shard_index": shard_index,
        "shard_total": shard_total,
        "mdx_repair_enabled_input": enabled_input == "true",
        "canary_locales": locales,
        "canary_paths": paths,
        "canary_gate_failure_policy": policy,
        "mdx_repair_gate_result": gate_result,
        "pending_locale_pages": pending,
        "pending_pages_outside_canary_scope": outside,
    }
    return enabled, reason, state


def decide_command(workspace: Path) -> None:
    enabled, reason, state = decide_canary(workspace)
    locale = str(state["locale"])
    state_path = workspace / ".openclaw-sync" / "mdx" / f"{locale}-canary-decision.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    enabled_token = "true" if enabled else "false"
    write_outputs({"enabled": enabled_token, "reason": reason})
    append_env({CANARY_ENV_VAR: enabled_token})
    print(json.dumps(state, sort_keys=True))


def gate_decision(evidence_dir: Path) -> tuple[str, str, str, dict[str, object]]:
    policy = (os.environ.get("CANARY_GATE_FAILURE_POLICY") or "fallback").strip().lower()
    if policy not in GATE_POLICIES:
        raise SystemExit(f"invalid CANARY_GATE_FAILURE_POLICY: {policy!r}; expected fallback or abort")
    result = (os.environ.get("MDX_REPAIR_GATE_RESULT") or "skipped").strip().lower()

    evidence = read_json(evidence_dir / "classification.json")
    file_classification = str((evidence or {}).get("classification") or "")
    file_reason = str((evidence or {}).get("reason") or "")

    if result == "skipped":
        decision, classification, reason = "not_applicable", "", "canary_switch_off"
    elif result == "success":
        if evidence is None:
            raise SystemExit(
                "release gate misconfiguration: the validation gate succeeded but its "
                "classification evidence is missing; failing closed before publication"
            )
        if file_classification != "success":
            raise SystemExit(
                "release gate misconfiguration: the validation gate succeeded but the "
                f"classification evidence says {file_classification or 'unknown'}"
            )
        decision, classification, reason = "pass", "success", file_reason or "validation_classification_success"
    elif result == "failure":
        classification = file_classification or "unknown"
        if classification != "unknown" and classification not in FAILURE_CLASSES:
            raise SystemExit(
                "release gate misconfiguration: the validation gate failed but the "
                f"classification evidence says {classification}"
            )
        reason = file_reason or "classification_evidence_missing"
        decision = "abort" if policy == "abort" else "fallback"
    else:
        raise SystemExit(f"unknown MDX repair gate result: {result!r}")

    record = {
        "event": "canary_release_gate",
        "gate_decision": decision,
        "classification": classification,
        "reason": reason,
        "policy": policy,
        "gate_result": result,
    }
    return decision, classification, reason, record


def gate_command(evidence_dir: Path) -> None:
    decision, classification, reason, record = gate_decision(evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "gate-decision.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    write_outputs({"gate_decision": decision, "classification": classification, "reason": reason})
    print(json.dumps(record, sort_keys=True))
    if decision == "abort":
        raise SystemExit(
            f"canary aborted: validation classification {classification} ({reason}); "
            "policy=abort stops before any publication step"
        )


def artifact_h1(page: Path) -> tuple[str, str]:
    """Derive the expected live h1 from the applied artifact page."""
    try:
        text = page.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "", f"artifact_page_missing_{sanitize_reason_token(page)}"
    body = text
    if body.startswith("---"):
        parts = body.split("---", 2)
        if len(parts) == 3:
            body = parts[2]
    for line in body.splitlines():
        heading = re.match(r"^#\s+(.+?)\s*#*\s*$", line)
        if heading:
            plain = re.sub(r"[`*_]", "", heading.group(1)).strip()
            return " ".join(plain.split()), ""
    title = re.search(r"(?m)^title:\s*['\"]?(.+?)['\"]?\s*$", text)
    if title:
        return " ".join(re.sub(r"[`*_]", "", title.group(1)).split()), ""
    return "", f"artifact_h1_missing_{sanitize_reason_token(page.name)}"


def r2_smoke_finish(outcome: str, reason: str, expected_h1: str, required: bool) -> None:
    write_outputs({"r2_smoke": outcome, "r2_smoke_reason": reason, "expected_h1": expected_h1})
    print(json.dumps({"r2_smoke": outcome, "reason": reason, "expected_h1": expected_h1}, sort_keys=True))
    if required and outcome != "verified":
        raise SystemExit(f"R2 content smoke finished {outcome}: {reason}")


def r2_smoke_command(locale: str, page_path: str, live_url: str, docs_root: Path, timeout: int, poll: int) -> None:
    required = (os.environ.get("R2_SMOKE_REQUIRE_VERIFIED") or "").strip() == "1"
    unverified_reason = (os.environ.get("R2_SMOKE_UNVERIFIED_REASON") or "").strip()
    if timeout < 1 or poll < 1:
        raise SystemExit("r2-smoke timeout-seconds and poll-seconds must be >= 1")

    page = None
    for candidate in (docs_root / locale / f"{page_path}.mdx", docs_root / locale / f"{page_path}.md"):
        if candidate.is_file():
            page = candidate
            break
    if page is None:
        missing = f"artifact_page_missing_{sanitize_reason_token(Path(locale) / page_path)}"
        r2_smoke_finish("unverified", missing, "", required)
        return
    expected_h1, note = artifact_h1(page)
    if unverified_reason:
        r2_smoke_finish("unverified", sanitize_reason_token(unverified_reason), expected_h1, required)
        return
    if page is None or not expected_h1:
        r2_smoke_finish("unverified", note, expected_h1, required)
        return
    if not live_url:
        r2_smoke_finish("unverified", "live_url_missing", expected_h1, required)
        return

    deadline = time.monotonic() + timeout
    last_h1 = ""
    while True:
        try:
            cache_buster = int(time.time())
            separator = "&" if "?" in live_url else "?"
            last_h1 = dispatch_r2_pages.extract_h1(
                dispatch_r2_pages.fetch_text(f"{live_url}{separator}_openclaw_i18n_canary={cache_buster}")
            )
            if last_h1 == expected_h1:
                r2_smoke_finish("verified", "live_h1_matches_artifact", expected_h1, required)
                return
        except Exception as exc:  # noqa: BLE001 - any fetch failure keeps polling until the deadline
            print(f"R2 smoke fetch failed: {exc}")
        if time.monotonic() >= deadline:
            break
        time.sleep(poll)
    r2_smoke_finish("mismatch", f"live_h1_mismatch_last_{sanitize_reason_token(last_h1)}", expected_h1, required)


def summary_record(artifact_dir: Path) -> dict[str, object]:
    locale = os.environ.get("LOCALE", "")
    locale_slug = os.environ.get("LOCALE_SLUG", "") or locale
    shard_index = os.environ.get("SHARD_INDEX", "0")
    shard_total = os.environ.get("SHARD_TOTAL", "1")
    metadata = read_json(artifact_dir / "metadata.json")
    report = read_json(artifact_dir / "mdx-repair-report.json")

    repair_mode = str((metadata or {}).get("mdx_repair_mode") or (report or {}).get("repair_mode") or "none")
    rounds = (metadata or {}).get("mdx_repair_rounds", (report or {}).get("rounds", 0))
    final_outcome = str(
        (metadata or {}).get("mdx_repair_final_outcome") or (report or {}).get("final_outcome") or "not_run"
    )
    failure_kind = str((report or {}).get("failure_kind") or "")
    repaired_pages = sorted(
        set((metadata or {}).get("mdx_repair_changed_paths") or [])  # type: ignore[arg-type]
        | {str(entry.get("path")) for entry in (report or {}).get("changed_paths") or [] if isinstance(entry, dict)}
    )
    failed_pages = sorted(
        set((metadata or {}).get("mdx_repair_failed_paths") or [])  # type: ignore[arg-type]
        | {str(entry.get("path")) for entry in (report or {}).get("failed_paths") or [] if isinstance(entry, dict)}
    )
    checker_intercepted = sorted(
        {
            str(entry.get("path"))
            for entry in (report or {}).get("violations") or []
            if isinstance(entry, dict) and entry.get("gate") == "checker"
        }
    )

    gate_decision = (os.environ.get("GATE_DECISION") or "").strip() or "not_applicable"
    gate_classification = (os.environ.get("GATE_CLASSIFICATION") or "").strip()
    gate_reason = (os.environ.get("GATE_REASON") or "").strip()
    policy = (os.environ.get("CANARY_GATE_FAILURE_POLICY") or "fallback").strip().lower()
    pages_dispatch_waited = (os.environ.get("PAGES_DISPATCH_WAITED") or "").strip() or "true"
    r2_outcome = (os.environ.get("R2_SMOKE_OUTCOME") or "").strip()
    r2_reason = (os.environ.get("R2_SMOKE_REASON") or "").strip()
    r2_expected_h1 = (os.environ.get("R2_SMOKE_EXPECTED_H1") or "").strip()
    if not r2_outcome:
        r2_outcome = "unverified"
        if not r2_reason:
            if (os.environ.get("ARTIFACT_ROLE") or "locale") != "canary":
                r2_reason = "locale_scope_publish_waits_on_r2_pages_run_page_content_not_diffed"
            else:
                r2_reason = "r2_smoke_step_did_not_run"

    risks: list[str] = []
    if metadata is None:
        risks.append("artifact_metadata_missing")
    if failed_pages:
        risks.append(f"pages_still_failing_{len(failed_pages)}")
    if checker_intercepted:
        risks.append(f"checker_intercepted_{len(checker_intercepted)}")
    if final_outcome == "final_failure":
        risks.append("relay_final_failure")
    if gate_decision == "fallback":
        risks.append(f"release_gate_fallback_{sanitize_reason_token(gate_classification or 'unknown')}")
    elif gate_decision == "abort":
        risks.append(f"release_gate_abort_{sanitize_reason_token(gate_classification or 'unknown')}")
    if r2_outcome != "verified":
        risks.append(f"r2_content_unverified_{sanitize_reason_token(r2_reason)}")
    if pages_dispatch_waited != "true":
        risks.append("pages_dispatch_not_waited")

    return {
        "event": "canary_release_summary",
        "locale": locale,
        "locale_slug": locale_slug,
        "shard": f"{shard_index}of{shard_total}",
        "artifact_role": (os.environ.get("ARTIFACT_ROLE") or "locale"),
        "repair": {
            "repair_mode": repair_mode,
            "rounds": rounds,
            "final_outcome": final_outcome,
            "failure_kind": failure_kind,
            "repaired_pages": repaired_pages,
            "checker_intercepted_pages": checker_intercepted,
            "failed_pages": failed_pages,
        },
        "release_gate": {
            "decision": gate_decision,
            "classification": gate_classification,
            "reason": gate_reason,
            "policy": policy,
        },
        "publish_integrity": {
            "pages_dispatch_waited": pages_dispatch_waited,
            "r2_content": {
                "outcome": r2_outcome,
                "reason": r2_reason,
                "expected_h1": r2_expected_h1,
            },
        },
        "remaining_risks": risks,
    }


def append_summary_markdown(record: dict[str, object]) -> None:
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary:
        return
    repair = record["repair"]  # type: ignore[index]
    gate = record["release_gate"]  # type: ignore[index]
    integrity = record["publish_integrity"]  # type: ignore[index]
    r2 = integrity["r2_content"]  # type: ignore[index]

    def paths_line(paths: object) -> str:
        items = [str(path) for path in paths]  # type: ignore[arg-type]
        return ", ".join(f"`{path}`" for path in items) if items else "none"

    with Path(summary).open("a", encoding="utf-8") as fh:
        fh.write(f"### Canary release summary ({record['locale']} shard {record['shard']})\n\n")  # type: ignore[index]
        fh.write(
            f"- release gate: `{gate['decision']}` classification=`{gate['classification'] or 'n/a'}` "  # type: ignore[index]
            f"policy=`{gate['policy']}` reason=`{gate['reason'] or 'n/a'}`\n"  # type: ignore[index]
        )
        fh.write(
            f"- mdx repair: mode=`{repair['repair_mode']}` rounds=`{repair['rounds']}` "  # type: ignore[index]
            f"final=`{repair['final_outcome']}`\n"
        )
        fh.write(f"- Codex repaired pages: {paths_line(repair['repaired_pages'])}\n")  # type: ignore[index]
        fh.write(f"- checker intercepted pages: {paths_line(repair['checker_intercepted_pages'])}\n")  # type: ignore[index]
        fh.write(f"- failed pages: {paths_line(repair['failed_pages'])}\n")  # type: ignore[index]
        fh.write(
            f"- publish integrity: pages dispatch waited=`{integrity['pages_dispatch_waited']}` "  # type: ignore[index]
            f"R2 content=`{r2['outcome']}` reason=`{r2['reason']}`\n"  # type: ignore[index]
        )
        risks = record["remaining_risks"]  # type: ignore[index]
        if risks:
            fh.write("- remaining risks:\n")
            for risk in risks:  # type: ignore[union-attr]
                fh.write(f"  - `{risk}`\n")
        else:
            fh.write("- remaining risks: none recorded\n")


def summary_command(artifact_dir: Path, workspace: Path) -> None:
    record = summary_record(artifact_dir)
    output_path = (
        workspace
        / ".openclaw-sync"
        / f"canary-release-summary-{record['locale_slug']}-s{record['shard']}.json"  # type: ignore[index]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    append_summary_markdown(record)
    print(json.dumps(record, sort_keys=True))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Canary switch, RELEASE gate, and release summary for the MDX repair relay.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Outputs:
  decide writes the canary decision JSON, GITHUB_OUTPUT enabled/reason, and GITHUB_ENV MDX_REPAIR_CANARY_ENABLED.
  gate writes gate-decision.json and GITHUB_OUTPUT gate_decision/classification/reason; abort exits non-zero.
  summary writes the release summary JSON and appends the release notes to GITHUB_STEP_SUMMARY.
  r2-smoke writes GITHUB_OUTPUT r2_smoke/r2_smoke_reason/expected_h1.

Examples:
  LOCALE=zh-CN LOCALE_SLUG=zh-CN SHARD_INDEX=0 SHARD_TOTAL=1 MDX_REPAIR_ENABLED_INPUT=true CANARY_LOCALES="zh-CN" CANARY_PATHS="channels/line.md" MDX_REPAIR_GATE_RESULT=success python .github/scripts/i18n/mdx_repair_canary.py decide
  MDX_REPAIR_GATE_RESULT=success python .github/scripts/i18n/mdx_repair_canary.py gate --evidence-dir .openclaw-sync/mdx-repair-gate
  LOCALE=zh-CN LOCALE_SLUG=zh-CN SHARD_INDEX=0 SHARD_TOTAL=1 python .github/scripts/i18n/mdx_repair_canary.py summary --artifact-dir .openclaw-sync/i18n-artifacts/zh-CN-s0of1
  LOCALE=zh-CN R2_SMOKE_REQUIRE_VERIFIED=1 python .github/scripts/i18n/mdx_repair_canary.py r2-smoke --locale zh-CN --page-path channels/line --live-url https://docs.openclaw.ai/zh-CN/channels/line
""",
    )
    parser.add_argument("command", choices=["decide", "gate", "summary", "r2-smoke"])
    parser.add_argument("--workspace", default=os.environ.get("GITHUB_WORKSPACE", "."), type=Path)
    parser.add_argument("--evidence-dir", default=".openclaw-sync/mdx-repair-gate", type=Path)
    parser.add_argument("--artifact-dir", default="", type=Path)
    parser.add_argument("--locale", default=os.environ.get("LOCALE", ""))
    parser.add_argument("--page-path", default="")
    parser.add_argument("--live-url", default="")
    parser.add_argument("--docs-root", default="docs", type=Path)
    parser.add_argument("--timeout-seconds", default=120, type=int)
    parser.add_argument("--poll-seconds", default=10, type=int)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "decide":
        decide_command(args.workspace.resolve())
    elif args.command == "gate":
        gate_command(args.evidence_dir)
    elif args.command == "summary":
        if not args.artifact_dir:
            raise SystemExit("summary requires --artifact-dir")
        summary_command(args.artifact_dir, args.workspace.resolve())
    else:
        if not args.page_path:
            raise SystemExit("r2-smoke requires --page-path")
        r2_smoke_command(
            args.locale,
            args.page_path,
            args.live_url,
            args.docs_root,
            args.timeout_seconds,
            args.poll_seconds,
        )


if __name__ == "__main__":
    main()
