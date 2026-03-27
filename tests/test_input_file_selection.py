import pathlib
import sys
import tempfile
import unittest
from datetime import date

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import generate_weekly_report as gwr


class InputFileSelectionTests(unittest.TestCase):
    def test_choose_latest_report_before_today(self):
        fn = getattr(gwr, "choose_input_report_file", None)
        self.assertIsNotNone(fn)

        with tempfile.TemporaryDirectory() as td:
            p = pathlib.Path(td)
            for name in [
                "周报2026-01-09.xlsx",
                "周报2026-02-10.xlsx",
                "周报2026-02-27.xlsx",
                "周报2026-03-06.xlsx",
                "notes.xlsx",
            ]:
                (p / name).touch()

            selected = fn(base_dir=p, today=date(2026, 3, 6), fallback_file="周报2026-01-09.xlsx")
            self.assertEqual(pathlib.Path(selected).name, "周报2026-02-27.xlsx")

    def test_choose_fallback_when_no_prior_report(self):
        fn = getattr(gwr, "choose_input_report_file", None)
        self.assertIsNotNone(fn)

        with tempfile.TemporaryDirectory() as td:
            p = pathlib.Path(td)
            (p / "周报2026-03-06.xlsx").touch()
            (p / "周报2026-01-09.xlsx").touch()

            selected = fn(base_dir=p, today=date(2026, 3, 6), fallback_file="周报2026-01-09.xlsx")
            self.assertEqual(pathlib.Path(selected).name, "周报2026-01-09.xlsx")

    def test_raise_when_no_candidate_and_no_fallback(self):
        fn = getattr(gwr, "choose_input_report_file", None)
        self.assertIsNotNone(fn)

        with tempfile.TemporaryDirectory() as td:
            p = pathlib.Path(td)
            with self.assertRaises(FileNotFoundError):
                fn(base_dir=p, today=date(2026, 3, 6), fallback_file="周报2026-01-09.xlsx")


if __name__ == "__main__":
    unittest.main()
