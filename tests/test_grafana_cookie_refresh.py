import importlib.util
import pathlib
import tempfile
import unittest
from unittest import mock


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "refresh_grafana_cookie.py"


def load_refresh_module():
    spec = importlib.util.spec_from_file_location("refresh_grafana_cookie", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GrafanaCookieRefreshTests(unittest.TestCase):
    def test_write_grafana_cookie_replaces_existing_line(self):
        module = load_refresh_module()

        with tempfile.TemporaryDirectory() as td:
            env_file = pathlib.Path(td) / ".env.local"
            env_file.write_text(
                "TXT_COOKIE=txt-session\n"
                "GRAFANA_COOKIE='grafana_session=old-value'\n"
                "GRAFANA_URL_BASE=https://grafana.example.com/api/datasources/proxy/1/api/v1\n",
                encoding="utf-8",
            )

            module.write_grafana_cookie(env_file, "grafana_session=new-value")

            self.assertEqual(
                env_file.read_text(encoding="utf-8"),
                "TXT_COOKIE=txt-session\n"
                "GRAFANA_COOKIE='grafana_session=new-value'\n"
                "GRAFANA_URL_BASE=https://grafana.example.com/api/datasources/proxy/1/api/v1\n",
            )

    def test_extract_grafana_cookie_from_response_cookie_jar(self):
        module = load_refresh_module()

        class FakeResponse:
            def __init__(self):
                self.cookies = {"grafana_session": "fresh-session"}

        self.assertEqual(
            module.extract_grafana_cookie(FakeResponse()),
            "grafana_session=fresh-session",
        )

    def test_extract_grafana_cookie_preserves_full_cookie_jar(self):
        module = load_refresh_module()

        class FakeResponse:
            def __init__(self):
                self.cookies = {
                    "grafana_session": "fresh-session",
                    "grafana_session_expiry": "1700000000",
                }

        self.assertEqual(
            module.extract_grafana_cookie(FakeResponse()),
            "grafana_session=fresh-session; grafana_session_expiry=1700000000",
        )

    def test_login_and_get_cookie_verifies_proxy_after_login(self):
        module = load_refresh_module()

        class FakeResponse:
            def __init__(self, status_code=200, payload=None):
                self.status_code = status_code
                self._payload = payload or {"status": "success"}
                self.cookies = {
                    "grafana_session": "fresh-session",
                    "grafana_session_expiry": "1700000000",
                }
                self.headers = {}

            def json(self):
                return self._payload

        class FakeSession:
            def __init__(self):
                self.calls = []
                self.cookies = {
                    "grafana_session": "fresh-session",
                    "grafana_session_expiry": "1700000000",
                }

            def post(self, url, **kwargs):
                self.calls.append((url, kwargs))
                if url.endswith("/login"):
                    return FakeResponse(payload={"message": "Logged in"})
                return FakeResponse()

        fake_session = FakeSession()
        with mock.patch.object(module.requests, "Session", return_value=fake_session):
            cookie_header = module.login_and_get_cookie(
                root_url="https://grafana.example.com",
                username="user",
                password="pass",
                timeout=15,
                grafana_url="https://grafana.example.com/api/datasources/proxy/7/api/v1/query_range",
                grafana_org_id="9",
            )

        self.assertEqual(
            cookie_header,
            "grafana_session=fresh-session; grafana_session_expiry=1700000000",
        )
        self.assertEqual(len(fake_session.calls), 2)
        self.assertEqual(fake_session.calls[1][0], "https://grafana.example.com/api/datasources/proxy/7/api/v1/query_range")
        self.assertEqual(
            fake_session.calls[1][1]["headers"]["x-grafana-org-id"],
            "9",
        )

    def test_weekly_job_refreshes_cookie_before_report_execution(self):
        script = (PROJECT_ROOT / "scripts" / "weekly_report_job.sh").read_text(encoding="utf-8")

        refresh_index = script.find("refresh_grafana_cookie.py")
        report_index = script.find("Running report script")

        self.assertGreaterEqual(refresh_index, 0)
        self.assertGreaterEqual(report_index, 0)
        self.assertLess(refresh_index, report_index)


if __name__ == "__main__":
    unittest.main()
