#!/usr/bin/env python3
"""Проверка качества заполнения ru-колонки в combined.csv."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Dict, List, Iterable

from tools.import_from_legacy_csvs import build_legacy_dictionary

PLACEHOLDER_RE = re.compile(r"\{[^{}]+\}")
TAG_RE = re.compile(r"\[/?[^\]]+\]|<br>|\\n")
SYMBOL_RE = re.compile(r"[%+\-]")
EVENT_HINT_RE = re.compile(r"EVENT|DIALOG|NPC|CUTSCENE|NARRATIVE", re.IGNORECASE)


def token_set(text: str, pattern: re.Pattern) -> List[str]:
    return sorted(pattern.findall(text or ""))


def normalization_length(text: str) -> int:
    stripped = TAG_RE.sub("", text or "")
    stripped = PLACEHOLDER_RE.sub("", stripped)
    return len(stripped.strip())


def top100(items: Iterable[dict]) -> List[dict]:
    return list(items)[:100]


def analyze(combined_path: Path, legacy_dir: Path) -> dict:
    legacy_map, _ = build_legacy_dictionary(legacy_dir)

    with combined_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        key_idx = header.index("KEY")
        en_idx = header.index("en")
        ru_idx = header.index("ru")

        report = {
            "missing_from_ru_source": [],
            "empty_ru": [],
            "same_as_en": [],
            "placeholder_mismatch": [],
            "markup_mismatch": [],
            "suspicious_shortening": [],
            "suspicious_event_or_dialog_trim": [],
            "machine_generated_candidates": [],
        }

        for line_no, row in enumerate(reader, start=2):
            if len(row) < len(header):
                row = row + [""] * (len(header) - len(row))

            key = row[key_idx].strip()
            if not key or key.startswith("//"):
                continue

            en = row[en_idx]
            ru = row[ru_idx]
            legacy_ru = legacy_map.get(key)

            if key not in legacy_map:
                report["missing_from_ru_source"].append({"key": key, "line": line_no})

            if not ru:
                report["empty_ru"].append({"key": key, "line": line_no})

            if ru and ru == en:
                report["same_as_en"].append({"key": key, "line": line_no})

            ph_en = token_set(en, PLACEHOLDER_RE)
            ph_ru = token_set(ru, PLACEHOLDER_RE)
            if ph_en != ph_ru:
                report["placeholder_mismatch"].append(
                    {"key": key, "line": line_no, "en": ph_en, "ru": ph_ru}
                )

            mk_en = token_set(en, TAG_RE) + token_set(en, SYMBOL_RE)
            mk_ru = token_set(ru, TAG_RE) + token_set(ru, SYMBOL_RE)
            if sorted(mk_en) != sorted(mk_ru):
                report["markup_mismatch"].append(
                    {"key": key, "line": line_no, "en": mk_en, "ru": mk_ru}
                )

            en_len = normalization_length(en)
            ru_len = normalization_length(ru)
            legacy_len = normalization_length(legacy_ru or "")

            if ru and en_len >= 30 and ru_len < int(en_len * 0.55):
                report["suspicious_shortening"].append(
                    {"key": key, "line": line_no, "en_len": en_len, "ru_len": ru_len}
                )
            elif ru and legacy_ru and legacy_len >= 30 and ru_len < int(legacy_len * 0.8):
                report["suspicious_shortening"].append(
                    {
                        "key": key,
                        "line": line_no,
                        "legacy_len": legacy_len,
                        "ru_len": ru_len,
                    }
                )

            if (
                ru
                and legacy_ru
                and (EVENT_HINT_RE.search(key) or en_len > 180 or legacy_len > 180)
                and legacy_len > 120
                and ru_len < int(legacy_len * 0.7)
            ):
                report["suspicious_event_or_dialog_trim"].append(
                    {
                        "key": key,
                        "line": line_no,
                        "legacy_len": legacy_len,
                        "ru_len": ru_len,
                    }
                )

    report["top_100"] = {
        k: top100(v) for k, v in report.items() if isinstance(v, list) and k != "machine_generated_candidates"
    }

    report["summary"] = {
        k: len(v)
        for k, v in report.items()
        if isinstance(v, list)
    }

    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Проверка качества ru-колонки в combined.csv")
    parser.add_argument("--combined", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--legacy-dir", default="data/text")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = analyze(Path(args.combined), Path(args.legacy_dir))

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Краткая сводка:")
    for category, count in report["summary"].items():
        print(f"- {category}: {count}")
    print(f"JSON-отчёт: {report_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
