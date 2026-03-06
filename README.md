# 🇷🇺 Mewgenics — Русский перевод

Неофициальный русский перевод для [Mewgenics](https://store.steampowered.com/app/686060/Mewgenics/) (Edmund McMillen & Tyler Glaiel, 2026).

## Важно про Build 22188119

После Build `22188119` игра читает локализацию из одного файла внутри `resources.gpak`:

- `data/text/combined.csv`
- язык берётся из колонки `ru`

Это значит, что старый подход с одними только `data/text/*.csv` больше **недостаточен**: теперь нужен патч `resources.gpak`.

## Быстрый старт

### Установка (патч resources.gpak)

```bash
python install.py --game-dir "D:/SteamLibrary/steamapps/common/Mewgenics" --extractor "C:/Tools/GPAK-Extractor.exe"
```

### Проверка качества текущего combined.csv

```bash
python install.py --check --game-dir "D:/SteamLibrary/steamapps/common/Mewgenics" --extractor "C:/Tools/GPAK-Extractor.exe"
```

### Dry-run

```bash
python install.py --dry-run --game-dir "D:/SteamLibrary/steamapps/common/Mewgenics" --extractor "C:/Tools/GPAK-Extractor.exe"
```

## Утилиты в `tools/`

- `tools/import_from_legacy_csvs.py` — импортирует legacy-переводы из `data/text/*.csv`, строит merge-отчёт (`imported_count`, `duplicate_key_conflicts`, `missing_keys`).
- `tools/build_ru_combined.py` — читает `combined.csv`, подставляет `ru` из legacy-переводов по `KEY`, сохраняет порядок строк и все колонки.
- `tools/check_translation.py` — запускает проверки качества `ru` (пустые строки, несовпадение плейсхолдеров/разметки, подозрительные сокращения и т.д.), пишет JSON-отчёт.
- `tools/patch_gpak.py` — автоматизирует распаковку/сборку `resources.gpak` через внешний `GPAK-Extractor`.

## Примеры ручного запуска

```bash
python -m tools.import_from_legacy_csvs --legacy-dir data/text --combined combined.csv --report merge_report.json
python -m tools.build_ru_combined --combined combined.csv --out combined_ru.csv --legacy-dir data/text
python -m tools.check_translation --combined combined_ru.csv --report check_report.json --legacy-dir data/text
python -m tools.patch_gpak --game-dir "D:/SteamLibrary/steamapps/common/Mewgenics" --extractor "C:/Tools/GPAK-Extractor.exe"
```

## Восстановление оригинала

При патче сохраняется `resources.gpak.bak` (если ещё не создан).

Чтобы откатиться:

1. Закройте игру.
2. Удалите изменённый `resources.gpak`.
3. Переименуйте `resources.gpak.bak` обратно в `resources.gpak`.

## Критичное предупреждение по качеству перевода

Нельзя машинно сокращать переводы описаний способностей, предметов, ивентов и NPC-диалогов.

Правила:

- не сокращать описания способностей и предметов;
- не обрезать нарративы событий и диалоги NPC;
- сохранять полный смысл и длину, если перевод уже есть;
- сохранять плейсхолдеры, спецтеги и разметку;
- если перевода нет — лучше оставить `ru` пустым и пометить это в отчёте;
- любые машинно сгенерированные кандидаты должны отмечаться отдельно в отчётах как `machine_generated_candidates`.

## Что не коммитить

Не добавляйте в git игровые бинарники и артефакты распаковки:

- `resources.gpak`
- `resources.gpak.bak` из папки игры
- `output.gpak`
- временные папки распаковки

## Лицензия

MIT
