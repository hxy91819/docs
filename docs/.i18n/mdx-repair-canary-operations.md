# MDX Repair Canary Operations (STORY-06)

Staged rollout, observation, and rollback drill for the enhanced existing Codex
repair relay (single entry: `openai/codex-action@v1`). This document is the
operator manual for the canary switch, the pre-publication RELEASE gate, the
release summary, and the rollback drill. It complements
`translation-workflow.md` and does not change any generated page.

Reference story: `plans/i18n-codex-mdx-fallback` STORY-06 (GC-06 canary →
scoped publish → live smoke → observation → rollback). Budgets and protocols
from D-09/D-10 are unchanged by the canary: `MDX_REPAIR_MAX_ATTEMPTS=4`,
`MDX_REPAIR_HARD_TIMEOUT_MS=600000`, `MDX_REPAIR_AUXILIARY_MODE=none`.

## 1. Switch contract (translate-locale-reusable.yml)

| Input | Default | Meaning |
| --- | --- | --- |
| `mdx_repair_enabled` | `false` | Master switch. `false` keeps the original failure path: every relay step is skipped and no new behavior runs (byte-equivalent default). |
| `canary_locales` | `""` | Comma-separated locale whitelist without spaces (`zh-CN,ja-JP`), exact token match. Empty = canary disabled everywhere. The decide script tolerates stray spaces, but the workflow-level gate expression does not, so a space-containing list fails closed instead of enabling the canary. |
| `canary_paths` | `""` | Comma/space separated locale-relative page prefixes (e.g. `channels/line.md` or `channels`). Every pending page of the shard must sit inside the whitelist. Empty = canary disabled. |
| `canary_gate_failure_policy` | `fallback` | What happens when the RELEASE gate classification is not `success`: `fallback` records it, disables the relay, and continues on the original failure path; `abort` fails the run before any publication. |

Fail-closed decision (`mdx_repair_canary.py decide`, one step per translate
job): the relay only starts when the master switch is on, the locale is an
exact member of `canary_locales`, all pending pages are inside `canary_paths`,
and the `mdx-repair-gate` job finished. The decision is recorded in the job
log and `.openclaw-sync/mdx/<locale>-canary-decision.json`, and exported as
`MDX_REPAIR_CANARY_ENABLED` for the relay step conditions. Any miss disables
the relay for that run without failing the job.

Manual dispatch exists on the reusable workflow (`workflow_dispatch`) with the
same inputs and defaults. A default dispatch behaves exactly like the
pre-canary workflow; it is the rollback drill entry (§5).

## 2. Pre-publication RELEASE gate

When `mdx_repair_enabled=true` and the locale is whitelisted, the
`mdx-repair-gate` job runs the STORY-05 validation sub-pipeline first by
reusing `.github/workflows/mdx-repair-validation.yml` via `workflow_call`
with `real_codex: true`. The translate job waits for it. The gate:

- succeeds only when the classification is `success`
  (`mdx_repair_validation.py classify`: success / agent_failure /
  environment_failure; evidence artifact
  `mdx-repair-validation-real-codex-<run_id>` holding `classification.json`);
- is consumed by the finalizer before commit or publish
  (`mdx_repair_canary.py gate`, which cross-checks the downloaded
  classification evidence against the gate job result; mismatches fail
  closed, and a successful gate without evidence fails closed);
- on `agent_failure`/`environment_failure`: records classification and
  reason in `gate-decision.json` and the step outputs, then either
  `fallback` (relay stays disabled for this run; the original failure path
  decides what publishes) or `abort` (the run fails before any publication
  step).

Because the gate runs before the relay, `fallback` coherently means "skip
repair": the translate job's decide step sees the failed gate and keeps
`MDX_REPAIR_CANARY_ENABLED=false`.

Cost note: every dispatched shard with the switch on triggers one real-Codex
validation run; the validation sub-pipeline serializes on its own concurrency
group. Keep the canary small (one locale, one shard) during observation.

## 3. Release summary (AC-03)

`Record canary release summary` (finalizer, only when the switch is on)
writes the release notes to the job step summary plus
`.openclaw-sync/canary-release-summary-<slug>-s<i>of<t>.json`, uploaded as
artifact `i18n-canary-release-summary-<slug>-s<i>of<t>-<source_sha>`
(retention 14 days). Fields:

- release gate: decision (`pass|fallback|abort|not_applicable`),
  classification, policy, reason;
- mdx repair: `repair_mode`, rounds, final outcome, failure kind;
- Codex repaired pages (changed paths), checker intercepted pages (relay
  checker violations), failed pages (`failed_paths`);
- publish integrity: whether the Pages dispatch was waited on, and the R2
  content verification record (`verified` / `unverified` with explicit
  reason / `mismatch`);
- remaining risks: stable tokens such as `pages_still_failing_<n>`,
  `release_gate_fallback_<class>`, `r2_content_unverified_<reason>`.

## 4. R2/Pages integrity (run 28273967200 lesson)

The historical failure dispatched the Pages router without an R2 content
upload, so the artifact was new but the live page stayed stale. The canary
lane now always ends with an explicit verification record:

- `canary_publish_required=true`: `dispatch_r2_pages.py` waits for the R2 run
  and the input-expected h1, then `Verify canary R2 content against artifact`
  (`mdx_repair_canary.py r2-smoke`) re-checks the live h1 against the h1
  derived from the applied artifact page. Mismatch or unverified fails the
  finalizer (`R2_SMOKE_REQUIRE_VERIFIED=1`).
- `canary_publish_required=false` (`--no-wait` lane): verification is recorded
  as `unverified` with reason
  `dispatch_no_wait_final_publication_covered_by_locale_full_deploys` —
  never silently claimed.
- Locale-scope publishes wait on the R2 Pages run; the summary records
  `locale_scope_publish_waits_on_r2_pages_run_page_content_not_diffed`
  (no single-page smoke is configured for full-locale deploys).

## 5. Enable, observe, rollback drill

Enable (observation run):

1. Pick one locale and one page path, e.g. `canary_locales="zh-CN"`,
   `canary_paths="channels/line.md"`, `artifact_role=canary`,
   `canary_live_path=channels/line`, `canary_publish_required=true`,
   `commit_locale=false`.
2. Dispatch through the normal entry (translate-incremental/translate-all
   canary lane) or `Actions → Translate Locale Reusable → Run workflow`.
3. Watch, in order: `mdx-repair-gate` (classification must be `success`),
   `Decide canary MDX repair scope` (decision JSON in the log), relay rounds
   and gates, the release summary, and the R2 smoke record.

Observe: keep the release summary artifact and the
`mdx-repair-validation-real-codex-<run_id>` evidence; compare
`remaining_risks` between runs; expand `canary_paths`/`canary_locales` only
after a clean observation window.

Rollback drill (AC-02, executable locally and in CI):

1. Local/CI dry run: `python -m pytest .github/scripts/i18n/tests/test_i18n_scripts.py -q`.
   The canary rollout tests evaluate the real workflow conditions and prove
   the switch-off plan is identical to the pre-canary plan (all 15 relay
   steps skip; finalize gains no active step).
2. Dispatch drill: run the reusable workflow with
   `mdx_repair_enabled=false` (all other inputs as usual). Expect: no
   `mdx-repair-gate` job, no relay steps, the strict check failure keeps the
   original failure semantics (artifact marked failed, no publish of failed
   pages).
3. Production rollback: re-dispatch (or let the next scheduled run happen)
   with the default inputs — the switch-off path is the rollback. A live
   `agent_failure`/`environment_failure` from the gate falls back or aborts
   automatically per `canary_gate_failure_policy`; to hard-stop a running
   rollout, cancel in-flight runs and keep the switch off.

Stop condition (STORY-06): any un-intercepted catastrophic deletion observed
online → switch off immediately, keep the artifacts, and escalate.

## 6. Boundaries

- No second Codex executor: the canary only gates enablement, scope, gate
  consumption, and reporting of the existing relay (D-09/D-10 budgets
  untouched).
- Default configuration (no new inputs) reproduces the previous behavior
  exactly; the gate job, gate consumption, R2 smoke, and release summary do
  not run when `mdx_repair_enabled=false`.
- Real canary execution happens only after the delivery push, coordinated
  with the repository owner.
