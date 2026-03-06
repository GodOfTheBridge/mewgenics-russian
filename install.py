#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from tools.patch_gpak import patch_game, run_attempts

EXE_NAME = "Mewgenics.exe"
GPAK_NAME = "resources.gpak"


def find_game_path() -> Path | None:
    steam_path = None

    if sys.platform == "win32":
        try:
            import winreg

            for reg_path in [r"SOFTWARE\WOW6432Node\Valve\Steam", r"SOFTWARE\Valve\Steam"]:
                try:
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path)
                    steam_path = winreg.QueryValueEx(key, "InstallPath")[0]
                    winreg.CloseKey(key)
                    break
                except OSError:
                    continue
        except ImportError:
            pass

    if not steam_path:
        for p in [
            os.path.expandvars(r"%ProgramFiles(x86)%\Steam"),
            os.path.expandvars(r"%ProgramFiles%\Steam"),
            r"C:\Steam",
            r"D:\Steam",
            r"E:\Steam",
        ]:
            if os.path.isdir(p):
                steam_path = p
                break

    if not steam_path:
        return None

    candidates = [Path(steam_path) / "steamapps" / "common" / "Mewgenics"]
    for c in candidates:
        if (c / EXE_NAME).exists() or (c / GPAK_NAME).exists():
            return c
    return None


def run_check(game_dir: Path, extractor: Path, legacy_dir: Path) -> int:
    if not extractor.exists():
        raise FileNotFoundError(f"Extractor не найден: {extractor}")

    resources = game_dir / GPAK_NAME
    if not resources.exists():
        raise FileNotFoundError(f"Не найден {resources}")

    with tempfile.TemporaryDirectory(prefix="mewgenics_check_") as temp_dir:
        temp_path = Path(temp_dir)
        extracted_dir = temp_path / "extracted"
        extracted_dir.mkdir(parents=True, exist_ok=True)

        run_attempts(
            [
                [str(extractor), "extract", str(resources), str(extracted_dir)],
                [str(extractor), "x", str(resources), str(extracted_dir)],
                [str(extractor), str(resources), str(extracted_dir)],
            ],
            success_check=lambda: (extracted_dir / "data" / "text" / "combined.csv").exists(),
        )

        combined = extracted_dir / "data" / "text" / "combined.csv"
        report = temp_path / "translation_check_report.json"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "tools.check_translation",
                "--combined",
                str(combined),
                "--report",
                str(report),
                "--legacy-dir",
                str(legacy_dir),
            ],
            check=True,
        )
        print(f"Проверка завершена. Отчёт: {report}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Установка русификатора через patch_gpak")
    parser.add_argument("--game-dir", help="Путь к папке Mewgenics")
    parser.add_argument("--extractor", required=True, help="Путь к GPAK-Extractor.exe")
    parser.add_argument("--check", action="store_true", help="Только проверка combined.csv")
    parser.add_argument("--dry-run", action="store_true", help="Показать действия без записи")
    parser.add_argument("--legacy-dir", default="data/text", help="Папка legacy CSV")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    game_dir = Path(args.game_dir) if args.game_dir else find_game_path()
    if game_dir is None:
        raise FileNotFoundError("Не удалось автоматически найти папку игры. Укажите --game-dir")

    if args.check:
        return run_check(game_dir, Path(args.extractor), Path(args.legacy_dir))

    patch_game(
        game_dir=game_dir,
        extractor=Path(args.extractor),
        legacy_dir=Path(args.legacy_dir),
        keep_temp=False,
        dry_run=args.dry_run,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
