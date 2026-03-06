#!/usr/bin/env python3
"""Сборка combined.csv с заполнением ru из legacy CSV."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import List, Tuple

from tools.import_from_legacy_csvs import build_legacy_dictionary


LANG_NAME_KEY = "CURRENT_LANGUAGE_NAME"
LANG_SHIPPABLE_KEY = "CURRENT_LANGUAGE_SHIPPABLE"


def fill_ru_rows(rows: List[List[str]], header: List[str], legacy_map: dict) -> Tuple[List[List[str]], dict]:
    key_idx = header.index("KEY")
    ru_idx = header.index("ru")

    stats = {
        "total_rows": 0,
        "imported_from_legacy": 0,
        "language_name_set": 0,
        "language_shippable_set": 0,
        "ru_filled_total": 0,
        "ru_empty_total": 0,
        "machine_generated_candidates": [],
    }

    output: List[List[str]] = [header]

    for row in rows:
        stats["total_rows"] += 1
        if len(row) < len(header):
            row = row + [""] * (len(header) - len(row))

        key = row[key_idx].strip() if len(row) > key_idx else ""
        if not key or key.startswith("//"):
            output.append(row)
            continue

        ru_val = row[ru_idx]
        legacy_val = legacy_map.get(key)
        if not ru_val and legacy_val is not None:
            row[ru_idx] = legacy_val
            stats["imported_from_legacy"] += 1

        if key == LANG_NAME_KEY and not row[ru_idx]:
            row[ru_idx] = "Русский"
            stats["language_name_set"] += 1

        if key == LANG_SHIPPABLE_KEY and not row[ru_idx]:
            row[ru_idx] = "yes"
            stats["language_shippable_set"] += 1

        if row[ru_idx]:
            stats["ru_filled_total"] += 1
        else:
            stats["ru_empty_total"] += 1

        output.append(row)

    return output, stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Заполняет ru-колонку в combined.csv")
    parser.add_argument("--combined", required=True, help="Путь к исходному combined.csv")
    parser.add_argument("--out", required=True, help="Путь для результирующего combined.csv")
    parser.add_argument("--legacy-dir", default="data/text", help="Папка legacy CSV")
    parser.add_argument("--dry-run", action="store_true", help="Только посчитать изменения")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    combined_path = Path(args.combined)
    out_path = Path(args.out)

    legacy_map, _ = build_legacy_dictionary(Path(args.legacy_dir))

    with combined_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header:
            raise ValueError("Пустой combined.csv")
        if "KEY" not in header or "ru" not in header:
            raise ValueError("combined.csv должен содержать колонки KEY и ru")
        rows = list(reader)

    updated_rows, stats = fill_ru_rows(rows, header, legacy_map)

    print(f"Всего строк: {stats['total_rows']}")
    print(f"Импортировано из legacy: {stats['imported_from_legacy']}")
    print(f"CURRENT_LANGUAGE_NAME выставлен: {stats['language_name_set']}")
    print(f"CURRENT_LANGUAGE_SHIPPABLE выставлен: {stats['language_shippable_set']}")
    print(f"ru заполнено: {stats['ru_filled_total']}, пусто: {stats['ru_empty_total']}")

    if args.dry_run:
        print("[dry-run] Файл не записан.")
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(updated_rows)

    print(f"Готово: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
