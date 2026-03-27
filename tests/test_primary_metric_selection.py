import pathlib
import sys
import unittest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import generate_weekly_report as gwr


class PrimaryMetricSelectionTests(unittest.TestCase):
    def test_resolve_primary_metric_prefers_grafana_for_odin(self):
        resolver = getattr(gwr, "resolve_primary_metric_value", None)
        self.assertIsNotNone(resolver)
        value, source = resolver("odin", {"p50": 12.9}, {"odin": 3210})
        self.assertEqual(value, 3210)
        self.assertEqual(source, "grafana_qps")

    def test_resolve_primary_metric_uses_p50_for_loki(self):
        resolver = getattr(gwr, "resolve_primary_metric_value", None)
        self.assertIsNotNone(resolver)
        value, source = resolver("视频Loki", {"p50": 12.9}, {})
        self.assertEqual(value, 12)
        self.assertEqual(source, "p50")

    def test_parse_txt_data_includes_p50_daily_avg(self):
        raw = {
            "body": {
                "data": [
                    {
                        "profiletype_0": "2",
                        "from_dt_0": "20260220",
                        "to_dt_0": "20260226",
                        "median_sum_0": 100,
                        "ninty_nine_sum_0": 200,
                        "nine_nine_nine_sum_0": 300,
                        "count_sum_0": 400,
                        "days_0": 4,
                    }
                ]
            }
        }

        parsed, latest = gwr.parse_txt_data(raw)
        self.assertEqual(latest, "20260220")
        metrics = parsed["2"]["20260220"]
        self.assertIn("p50", metrics)
        self.assertEqual(metrics["p50"], 25.0)


if __name__ == "__main__":
    unittest.main()
