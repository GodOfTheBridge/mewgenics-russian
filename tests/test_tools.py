import csv
import tempfile
import unittest
from pathlib import Path

from tools.build_ru_combined import fill_ru_rows
from tools.check_translation import analyze
from tools.import_from_legacy_csvs import build_legacy_dictionary


class ToolsTests(unittest.TestCase):
    def test_legacy_import_and_conflicts(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "a.csv").write_text("KEY,en\nK1,Текст 1\nK2,Текст 2\n", encoding="utf-8-sig")
            (base / "b.csv").write_text("KEY,en\nK2,Другой\nK3,Текст 3\n", encoding="utf-8-sig")
            mapping, conflicts = build_legacy_dictionary(base)
            self.assertEqual(mapping["K2"], "Текст 2")
            self.assertEqual(mapping["K3"], "Текст 3")
            self.assertEqual(len(conflicts), 1)

    def test_fill_ru_combined_and_language_keys(self):
        header = ["KEY", "en", "ru", "extra"]
        rows = [
            ["// abilities.csv", "", "", ""],
            ["CURRENT_LANGUAGE_NAME", "English", "", "x"],
            ["CURRENT_LANGUAGE_SHIPPABLE", "yes", "", "x"],
            ["ABILITY_X_DESC", "Deal {v0} dmg, +1 [b]stack[/b]", "", "z"],
            ["DIALOG_LONG", "Narrative long text", "", "z"],
        ]
        legacy = {
            "ABILITY_X_DESC": "Нанести {v0} урона, +1 [b]стак[/b]",
            "DIALOG_LONG": "Очень длинный нарратив без сокращений, с запятыми, \"кавычками\" и деталями.",
        }
        out, stats = fill_ru_rows(rows, header, legacy)
        by_key = {r[0]: r for r in out[1:] if r and not r[0].startswith("//")}

        self.assertEqual(by_key["CURRENT_LANGUAGE_NAME"][2], "Русский")
        self.assertEqual(by_key["CURRENT_LANGUAGE_SHIPPABLE"][2], "yes")
        self.assertIn("{v0}", by_key["ABILITY_X_DESC"][2])
        self.assertIn("[b]", by_key["ABILITY_X_DESC"][2])
        self.assertIn("кавычками", by_key["DIALOG_LONG"][2])
        self.assertGreater(stats["imported_from_legacy"], 0)

    def test_csv_roundtrip_quotes_and_commas(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "combined.csv"
            out = Path(tmp) / "out.csv"
            rows = [
                ["KEY", "en", "ru"],
                ["ITEM_DESC", 'Text with, comma and "quote"', ""],
            ]
            with path.open("w", encoding="utf-8-sig", newline="") as f:
                csv.writer(f).writerows(rows)

            with path.open("r", encoding="utf-8-sig", newline="") as f:
                reader = csv.reader(f)
                header = next(reader)
                body = list(reader)

            updated, _ = fill_ru_rows(body, header, {"ITEM_DESC": 'Текст, с запятой и "кавычкой"'})
            with out.open("w", encoding="utf-8-sig", newline="") as f:
                csv.writer(f).writerows(updated)

            with out.open("r", encoding="utf-8-sig", newline="") as rf:
                parsed = list(csv.reader(rf))
            self.assertEqual(parsed[1][2], 'Текст, с запятой и "кавычкой"')

    def test_check_detects_placeholder_and_trim(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            legacy_dir = base / "legacy"
            legacy_dir.mkdir()
            (legacy_dir / "events.csv").write_text(
                "KEY,en\nNPC_DIALOG_1,Очень длинный текст диалога с деталями и вставками {v0} и [b]тегами[/b], который нельзя сокращать.\n",
                encoding="utf-8-sig",
            )
            combined = base / "combined.csv"
            with combined.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["KEY", "en", "ru"])
                writer.writerow(["NPC_DIALOG_1", "Very long dialog {v0} [b]text[/b]", "Коротко"])

            report = analyze(combined, legacy_dir)
            self.assertTrue(report["placeholder_mismatch"])
            self.assertTrue(report["suspicious_shortening"])


if __name__ == "__main__":
    unittest.main()
