#!/usr/bin/env python3
"""Импорт переводов из legacy CSV (data/text/*.csv)."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple


def _iter_legacy_csv_rows(csv_path: Path):
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            yield row


def build_legacy_dictionary(legacy_dir: Path) -> Tuple[Dict[str, str], List[dict]]:
    legacy_map: Dict[str, str] = {}
    conflicts: List[dict] = []

    for csv_path in sorted(legacy_dir.glob("*.csv")):
        first_row = True
        for row_num, row in enumerate(_iter_legacy_csv_rows(csv_path), start=1):
            if not row:
                continue

            key = (row[0] if len(row) > 0 else "").strip()
            if first_row and key == "KEY":
                first_row = False
                continue
            first_row = False

            if not key or key.startswith("//"):
                continue

            value = row[1] if len(row) > 1 else ""

            if key in legacy_map and legacy_map[key] != value:
                conflicts.append(
                    {
                        "key": key,
                        "kept_value": legacy_map[key],
                        "new_value": value,
                        "file": str(csv_path),
                        "row": row_num,
                    }
                )
                continue

            legacy_map.setdefault(key, value)

    return legacy_map, conflicts


def collect_combined_keys(combined_csv: Path) -> List[str]:
    keys: List[str] = []
    with combined_csv.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header:
            return keys
        try:
            key_idx = header.index("KEY")
        except ValueError:
            return keys

        for row in reader:
            if len(row) <= key_idx:
                continue
            key = row[key_idx].strip()
            if key and not key.startswith("//"):
                keys.append(key)
    # Убираем дубли, сохраняя порядок первого появления
    return list(dict.fromkeys(keys))


def build_report(legacy_map: Dict[str, str], conflicts: List[dict], missing_keys: List[str]) -> dict:
    return {
        "imported_count": len(legacy_map),
        "duplicate_key_conflicts": conflicts,
        "missing_keys": missing_keys,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Импорт legacy-переводов из data/text/*.csv")
    parser.add_argument("--legacy-dir", default="data/text", help="Папка с legacy CSV")
    parser.add_argument("--combined", help="combined.csv для поиска missing_keys")
    parser.add_argument("--report", help="Путь для JSON-отчёта")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    legacy_dir = Path(args.legacy_dir)

    if not legacy_dir.exists():
        raise FileNotFoundError(f"Папка legacy CSV не найдена: {legacy_dir}")

    legacy_map, conflicts = build_legacy_dictionary(legacy_dir)

    if conflicts:
        print(f"[warning] Найдены конфликты ключей: {len(conflicts)}")

    missing_keys: List[str] = []
    if args.combined:
        combined_path = Path(args.combined)
        if not combined_path.exists():
            raise FileNotFoundError(f"combined.csv не найден: {combined_path}")
        combined_keys = collect_combined_keys(combined_path)
        missing_keys = [k for k in combined_keys if k not in legacy_map]

    report = build_report(legacy_map, conflicts, missing_keys)

    print(f"Импортировано ключей: {report['imported_count']}")
    print(f"Конфликтов дубликатов: {len(report['duplicate_key_conflicts'])}")
    print(f"Отсутствует в legacy: {len(report['missing_keys'])}")

    if args.report:
        report_path = Path(args.report)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Отчёт сохранён: {report_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
