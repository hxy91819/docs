#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path


OPEN_TAGS = {
    "Accordion": re.compile(r"^\s*<Accordion\b[^>]*>\s*$"),
    "AccordionGroup": re.compile(r"^\s*<AccordionGroup>\s*$"),
}

CLOSE_TAGS = {
    "Accordion": "</Accordion>",
    "AccordionGroup": "</AccordionGroup>",
}

OPEN_COUNT_PATTERNS = {
    "Accordion": re.compile(r"<Accordion\b(?!Group\b)[^>]*>"),
    "AccordionGroup": re.compile(r"<AccordionGroup>"),
}

CLOSE_COUNT_PATTERNS = {
    "Accordion": re.compile(r"</Accordion>"),
    "AccordionGroup": re.compile(r"</AccordionGroup>"),
}

CODE_FENCE_RE = re.compile(r"^\s*```")


@dataclass
class ValidationResult:
    source_path: Path
    localized_path: Path
    fix_applied: bool
    remaining_errors: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate localized MD/MDX output and apply safe deterministic repairs."
    )
    parser.add_argument("--docs-root", required=True)
    parser.add_argument("--locale", required=True)
    parser.add_argument("--pending-file", required=True)
    parser.add_argument("--invalid-file", required=True)
    parser.add_argument("--report-file")
    return parser.parse_args()


def count_matches(pattern: re.Pattern[str], text: str) -> int:
    return len(pattern.findall(text))


def collect_metrics(path: Path) -> dict[str, int]:
    text = path.read_text(encoding="utf-8")
    metrics: dict[str, int] = {}
    for name, pattern in OPEN_COUNT_PATTERNS.items():
        metrics[f"{name}_open"] = count_matches(pattern, text)
    for name, pattern in CLOSE_COUNT_PATTERNS.items():
        metrics[f"{name}_close"] = count_matches(pattern, text)
    metrics["code_fence"] = sum(1 for line in text.splitlines() if CODE_FENCE_RE.match(line))
    return metrics


def stack_validate(text: str) -> tuple[list[str], list[str]]:
    stack: list[str] = []
    errors: list[str] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        matched_open = next((name for name, pattern in OPEN_TAGS.items() if pattern.match(stripped)), None)
        if matched_open:
            stack.append(matched_open)
            continue

        matched_close = next((name for name, value in CLOSE_TAGS.items() if stripped == value), None)
        if not matched_close:
            continue
        if not stack:
            errors.append(f"line {lineno}: unexpected {CLOSE_TAGS[matched_close]}")
            continue
        top = stack[-1]
        if top != matched_close:
            errors.append(
                f"line {lineno}: closing {CLOSE_TAGS[matched_close]} while {top} is still open"
            )
            continue
        stack.pop()
    return stack, errors


def last_nonempty_line(text: str) -> str:
    for line in reversed(text.splitlines()):
        if line.strip():
            return line.strip()
    return ""


def deterministic_repair_allowed(
    source_metrics: dict[str, int],
    localized_metrics: dict[str, int],
    stack_errors: list[str],
    unclosed_stack: list[str],
) -> bool:
    if stack_errors:
        return False
    if not unclosed_stack and localized_metrics["code_fence"] % 2 == 0:
        return False
    for name in OPEN_TAGS:
        if localized_metrics[f"{name}_open"] != source_metrics[f"{name}_open"]:
            return False
    return True


def apply_deterministic_repair(path: Path, text: str, unclosed_stack: list[str]) -> bool:
    lines = text.splitlines()
    trailing_newline = text.endswith("\n")
    last_line = last_nonempty_line(text)
    if any(pattern.match(last_line) for pattern in OPEN_TAGS.values()):
        return False

    changed = False
    if sum(1 for line in lines if CODE_FENCE_RE.match(line)) % 2 == 1:
        lines.append("```")
        changed = True

    if unclosed_stack:
        if lines and lines[-1].strip():
            lines.append("")
        for tag_name in reversed(unclosed_stack):
            lines.append(CLOSE_TAGS[tag_name])
        changed = True

    if not changed:
        return False

    output = "\n".join(lines)
    if trailing_newline or changed:
        output += "\n"
    path.write_text(output, encoding="utf-8")
    return True


def validate_one(docs_root: Path, locale: str, source_path: Path) -> ValidationResult:
    rel = source_path.relative_to(docs_root)
    localized_path = docs_root / locale / rel
    if not localized_path.exists():
        return ValidationResult(source_path, localized_path, False, ["missing localized file"])

    source_metrics = collect_metrics(source_path)
    text = localized_path.read_text(encoding="utf-8")
    localized_metrics = collect_metrics(localized_path)
    unclosed_stack, stack_errors = stack_validate(text)

    errors = list(stack_errors)
    for name in OPEN_TAGS:
        source_open = source_metrics[f"{name}_open"]
        localized_open = localized_metrics[f"{name}_open"]
        if localized_open != source_open:
            errors.append(
                f"{name} open-count mismatch: source={source_open} localized={localized_open}"
            )
    for name in OPEN_TAGS:
        localized_open = localized_metrics[f"{name}_open"]
        localized_close = localized_metrics[f"{name}_close"]
        if localized_close > localized_open:
            errors.append(
                f"{name} close-count mismatch: localized_open={localized_open} localized_close={localized_close}"
            )
    if localized_metrics["code_fence"] % 2 == 1:
        errors.append("unclosed code fence at EOF")
    if unclosed_stack:
        errors.append(f"unclosed tags at EOF: {', '.join(unclosed_stack)}")

    fix_applied = False
    if errors and deterministic_repair_allowed(source_metrics, localized_metrics, stack_errors, unclosed_stack):
        fix_applied = apply_deterministic_repair(localized_path, text, unclosed_stack)
        if fix_applied:
            text = localized_path.read_text(encoding="utf-8")
            localized_metrics = collect_metrics(localized_path)
            unclosed_stack, stack_errors = stack_validate(text)
            errors = list(stack_errors)
            for name in OPEN_TAGS:
                source_open = source_metrics[f"{name}_open"]
                localized_open = localized_metrics[f"{name}_open"]
                if localized_open != source_open:
                    errors.append(
                        f"{name} open-count mismatch: source={source_open} localized={localized_open}"
                    )
                localized_close = localized_metrics[f"{name}_close"]
                if localized_close > localized_open:
                    errors.append(
                        f"{name} close-count mismatch: localized_open={localized_open} localized_close={localized_close}"
                    )
            if localized_metrics["code_fence"] % 2 == 1:
                errors.append("unclosed code fence at EOF")
            if unclosed_stack:
                errors.append(f"unclosed tags at EOF: {', '.join(unclosed_stack)}")

    return ValidationResult(source_path, localized_path, fix_applied, errors)


def load_pending_paths(path: Path) -> list[Path]:
    if not path.exists():
        return []
    items = [Path(line.strip()) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    seen: set[Path] = set()
    ordered: list[Path] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def main() -> int:
    args = parse_args()
    docs_root = Path(args.docs_root).resolve()
    pending_file = Path(args.pending_file)
    invalid_file = Path(args.invalid_file)
    report_file = Path(args.report_file) if args.report_file else None

    results: list[ValidationResult] = []
    for source_path in load_pending_paths(pending_file):
        results.append(validate_one(docs_root, args.locale, source_path.resolve()))

    invalid_sources = [result.source_path for result in results if result.remaining_errors]
    invalid_file.parent.mkdir(parents=True, exist_ok=True)
    invalid_file.write_text(
        "".join(f"{path}\n" for path in invalid_sources),
        encoding="utf-8",
    )

    if report_file:
        report_file.parent.mkdir(parents=True, exist_ok=True)
        payload = [
            {
                "source_path": str(result.source_path),
                "localized_path": str(result.localized_path),
                "fix_applied": result.fix_applied,
                "remaining_errors": result.remaining_errors,
            }
            for result in results
        ]
        report_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    for result in results:
        if result.remaining_errors:
            print(f"INVALID {result.localized_path}")
            for error in result.remaining_errors:
                print(f"  - {error}")
        elif result.fix_applied:
            print(f"FIXED {result.localized_path}")
        else:
            print(f"OK {result.localized_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
