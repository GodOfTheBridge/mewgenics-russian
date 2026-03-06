#!/usr/bin/env python3
"""Патч resources.gpak через внешний GPAK Extractor."""

from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List

from tools.build_ru_combined import fill_ru_rows
from tools.import_from_legacy_csvs import build_legacy_dictionary


def run_attempts(attempts: List[List[str]], success_check=None) -> None:
    last_error = None
    for cmd in attempts:
        try:
            subprocess.run(cmd, check=True)
            if success_check is None or success_check():
                return
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"Не удалось выполнить команду экстрактора. Последняя ошибка: {last_error}")


def find_resources_gpak(game_dir: Path) -> Path:
    gpak_path = game_dir / "resources.gpak"
    if not gpak_path.exists():
        raise FileNotFoundError(f"resources.gpak не найден в {game_dir}")
    return gpak_path


def count_ru(combined_csv: Path) -> tuple[int, int]:
    with combined_csv.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        key_idx = header.index("KEY")
        ru_idx = header.index("ru")
        filled = 0
        empty = 0
        for row in reader:
            if len(row) <= max(key_idx, ru_idx):
                continue
            key = row[key_idx].strip()
            if not key or key.startswith("//"):
                continue
            if row[ru_idx]:
                filled += 1
            else:
                empty += 1
    return filled, empty


def patch_game(game_dir: Path, extractor: Path, legacy_dir: Path, keep_temp: bool, dry_run: bool) -> None:
    if not extractor.exists():
        raise FileNotFoundError(f"Extractor не найден: {extractor}")

    gpak_path = find_resources_gpak(game_dir)
    backup_path = game_dir / "resources.gpak.bak"

    if not backup_path.exists() and not dry_run:
        shutil.copy2(gpak_path, backup_path)
        print(f"Создан backup: {backup_path}")

    temp_root = Path(tempfile.mkdtemp(prefix="mewgenics_gpak_"))

    try:
        extracted_dir = temp_root / "extracted"
        extracted_dir.mkdir(parents=True, exist_ok=True)

        print("Распаковка resources.gpak...")
        run_attempts(
            [
                [str(extractor), "extract", str(gpak_path), str(extracted_dir)],
                [str(extractor), "x", str(gpak_path), str(extracted_dir)],
                [str(extractor), str(gpak_path), str(extracted_dir)],
            ],
            success_check=lambda: (extracted_dir / "data" / "text" / "combined.csv").exists(),
        )

        combined_path = extracted_dir / "data" / "text" / "combined.csv"
        if not combined_path.exists():
            raise FileNotFoundError("В распакованном архиве не найден data/text/combined.csv")

        legacy_map, _ = build_legacy_dictionary(legacy_dir)
        with combined_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            header = next(reader)
            rows = list(reader)

        updated_rows, _stats = fill_ru_rows(rows, header, legacy_map)

        if not dry_run:
            with combined_path.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerows(updated_rows)

            repacked_path = temp_root / "resources.gpak"
            print("Упаковка resources.gpak...")
            run_attempts(
                [
                    [str(extractor), "pack", str(extracted_dir), str(repacked_path)],
                    [str(extractor), "c", str(extracted_dir), str(repacked_path)],
                ],
                success_check=lambda: repacked_path.exists(),
            )

            shutil.copy2(repacked_path, gpak_path)
            print(f"resources.gpak обновлён: {gpak_path}")
        else:
            print("[dry-run] Патч не записан в resources.gpak")

        filled, empty = count_ru(combined_path)
        print(f"ru заполнено: {filled}, ru пусто: {empty}")
    finally:
        if keep_temp:
            print(f"Временная папка сохранена: {temp_root}")
        else:
            shutil.rmtree(temp_root, ignore_errors=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Патч resources.gpak через combined.csv")
    parser.add_argument("--game-dir", required=True)
    parser.add_argument("--extractor", required=True, help="Путь к GPAK-Extractor.exe")
    parser.add_argument("--legacy-dir", default="data/text")
    parser.add_argument("--keep-temp", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    patch_game(
        game_dir=Path(args.game_dir),
        extractor=Path(args.extractor),
        legacy_dir=Path(args.legacy_dir),
        keep_temp=args.keep_temp,
        dry_run=args.dry_run,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
