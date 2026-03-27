import importlib.util
import os
import pathlib
import sys
import tempfile
import types
import unittest
from unittest import mock

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "generate_weekly_report.py"


def load_generate_module():
    spec = importlib.util.spec_from_file_location("generate_weekly_report_under_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)

    fake_pandas = types.ModuleType("pandas")
    fake_openpyxl = types.ModuleType("openpyxl")
    fake_styles = types.ModuleType("openpyxl.styles")

    class DummyStyle:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    fake_styles.Font = DummyStyle
    fake_styles.Alignment = DummyStyle
    fake_styles.Border = DummyStyle
    fake_styles.Side = DummyStyle
    fake_styles.PatternFill = DummyStyle
    fake_openpyxl.styles = fake_styles

    with mock.patch.dict(
        sys.modules,
        {
            "pandas": fake_pandas,
            "openpyxl": fake_openpyxl,
            "openpyxl.styles": fake_styles,
        },
        clear=False,
    ):
        assert spec.loader is not None
        spec.loader.exec_module(module)
    return module


gwr = load_generate_module()


class FakeCell:
    def __init__(self):
        self.value = None


class FakeWorksheet:
    def __init__(self):
        self._cells = {}

    def cell(self, row, column):
        key = (row, column)
        if key not in self._cells:
            self._cells[key] = FakeCell()
        return self._cells[key]


class GrafanaQpsHandlingTests(unittest.TestCase):
    def test_parse_grafana_max_qps_unauthorized(self):
        raw = {"message": "Unauthorized"}
        qps, err = gwr.parse_grafana_max_qps(raw)
        self.assertIsNone(qps)
        self.assertEqual(err, "unauthorized")

    def test_parse_grafana_max_qps_success(self):
        raw = {
            "status": "success",
            "data": {
                "result": [
                    {"values": [[1, "12.5"], [2, "20"], [3, "19.9"]]}
                ]
            },
        }
        qps, err = gwr.parse_grafana_max_qps(raw)
        self.assertEqual(qps, 20.0)
        self.assertIsNone(err)

    def test_write_qps_value_clears_stale_cell(self):
        ws = FakeWorksheet()
        ws.cell(row=1, column=1).value = 999
        gwr.write_qps_value(ws, 1, 1, None)
        self.assertIsNone(ws.cell(row=1, column=1).value)

    def test_fetch_grafana_data_prefers_fresh_env_file_cookie(self):
        with tempfile.TemporaryDirectory() as td:
            env_file = pathlib.Path(td) / ".env.local"
            env_file.write_text(
                "GRAFANA_COOKIE='grafana_session=fresh-session; grafana_session_expiry=1700000000'\n"
                "GRAFANA_URL=https://grafana.example.com/api/datasources/proxy/7/api/v1/query_range\n"
                "GRAFANA_ORG_ID='9'\n",
                encoding="utf-8",
            )

            captured = {}

            class FakeResponse:
                status_code = 200

                def json(self):
                    return {"status": "success", "data": {"result": []}}

            def fake_post(url, headers, data, verify):
                captured["url"] = url
                captured["headers"] = headers
                captured["data"] = data
                captured["verify"] = verify
                return FakeResponse()

            with mock.patch.dict(
                os.environ,
                {
                    "GRAFANA_COOKIE": "grafana_session=stale-session",
                    "GRAFANA_URL": "https://stale.example.com/query_range",
                    "GRAFANA_ORG_ID": "1",
                },
                clear=False,
            ):
                with mock.patch.object(gwr.requests, "post", side_effect=fake_post):
                    gwr.fetch_grafana_data("umab-odin-interface", 1, 2, env_file=env_file)

        self.assertEqual(
            captured["url"],
            "https://grafana.example.com/api/datasources/proxy/7/api/v1/query_range",
        )
        self.assertEqual(
            captured["headers"]["cookie"],
            "grafana_session=fresh-session; grafana_session_expiry=1700000000",
        )
        self.assertEqual(captured["headers"]["x-grafana-org-id"], "9")


if __name__ == "__main__":
    unittest.main()
