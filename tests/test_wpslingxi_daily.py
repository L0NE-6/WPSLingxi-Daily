import contextlib
import io
import json
import os
import tempfile
import time
import unittest
from unittest import mock

import wpslingxi_daily as daily


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.headers = {}
        self.closed = False

    def request(self, method, url, **kwargs):
        self.calls.append({"method": method, "url": url, "json": kwargs.get("json")})
        if not self.responses:
            raise AssertionError("unexpected request")
        return self.responses.pop(0)

    def close(self):
        self.closed = True


class FakeCookieCloud:
    def __init__(self, payload):
        self.payload = payload

    def get_decrypted_data(self):
        return self.payload


class SlowCookieCloud:
    def get_decrypted_data(self):
        time.sleep(0.2)
        return {}


def task(status="claimable", today=None):
    return {
        "task_key": "daily_check_in",
        "status": status,
        "extra": {
            "consecutive_days": 2,
            "check_in_days": [{"date": today or daily.beijing_today(), "status": "locked"}],
        },
        "reward_amount": 10,
    }


def account():
    return daily.Account("主号", "wps_sid=abc; uid=1")


class WpsLingxiDailyTests(unittest.TestCase):
    def test_parse_cookie_and_uid(self):
        accounts = daily.parse_accounts("主号|wps_sid=abc; uid=1\n备号|xyz|2")
        self.assertEqual(accounts[0].cookie, "wps_sid=abc; uid=1")
        self.assertEqual(accounts[1].cookie, "wps_sid=xyz; uid=2")

    def test_parse_cookie_accepts_uppercase_wps_sid(self):
        accounts = daily.parse_accounts("主号|WPS_SID=abc; uid=1")
        self.assertEqual(accounts[0].cookie, "WPS_SID=abc; uid=1")

    def test_parse_cookiecloud_profiles_with_password_pipes(self):
        profiles = daily.parse_cookiecloud_profiles(
            "# comment\n主号|https://cookie.example/api|uuid-1|p|with|pipes\n"
            "备号|http://127.0.0.1:8088|uuid-2|password"
        )
        self.assertEqual(len(profiles), 2)
        self.assertEqual(profiles[0].label, "主号")
        self.assertEqual(profiles[0].password, "p|with|pipes")

    def test_cookiecloud_partial_single_config_is_explicit(self):
        with mock.patch.dict(
            os.environ,
            {
                "WPSLINGXI_COOKIECLOUD_PROFILES": "",
                "WPSLINGXI_COOKIECLOUD_URL": "https://cookie.example",
                "WPSLINGXI_COOKIECLOUD_UUID": "",
                "WPSLINGXI_COOKIECLOUD_PASSWORD": "",
            },
            clear=False,
        ):
            with self.assertRaises(daily.CookieCloudError):
                daily.parse_cookiecloud_profiles()

    def test_explicit_profile_text_does_not_merge_environment_single(self):
        with mock.patch.dict(
            os.environ,
            {
                "WPSLINGXI_COOKIECLOUD_PROFILES": "环境|https://env.example|u|p",
                "WPSLINGXI_COOKIECLOUD_URL": "https://single.example",
                "WPSLINGXI_COOKIECLOUD_UUID": "uuid",
                "WPSLINGXI_COOKIECLOUD_PASSWORD": "password",
            },
            clear=False,
        ):
            profiles = daily.parse_cookiecloud_profiles(
                "显式|https://explicit.example|u2|p2"
            )
        self.assertEqual(len(profiles), 1)
        self.assertEqual(profiles[0].label, "显式")

    def test_cookiecloud_extracts_wps_domain_and_uid(self):
        cookie = daily.extract_cookiecloud_cookie(
            {
                "lingxi.wps.cn": [
                    {"name": "wps_sid", "value": "sid-1"},
                    {"name": "uid", "value": "42"},
                ]
            },
            label="主号",
        )
        self.assertEqual(cookie, "wps_sid=sid-1; uid=42")

    def test_cookiecloud_falls_back_to_kdocs_domain(self):
        cookie = daily.extract_cookiecloud_cookie(
            {
                "lingxi.kdocs.cn": [
                    {"name": "wps_sid", "value": "sid-2"},
                    {"name": "uid", "value": "7"},
                ]
            },
            label="备号",
        )
        self.assertEqual(cookie, "wps_sid=sid-2; uid=7")

    def test_cookiecloud_prefers_primary_domain(self):
        cookie = daily.extract_cookiecloud_cookie(
            {
                "lingxi.kdocs.cn": [{"name": "wps_sid", "value": "fallback"}],
                "lingxi.wps.cn": [{"name": "wps_sid", "value": "primary"}],
            },
            label="主号",
        )
        self.assertEqual(cookie, "wps_sid=primary")

    def test_cookiecloud_does_not_mix_uid_from_another_domain(self):
        cookie = daily.extract_cookiecloud_cookie(
            {
                "lingxi.wps.cn": [{"name": "wps_sid", "value": "primary"}],
                "other.wps.cn": [{"name": "uid", "value": "wrong-session"}],
            },
            label="主号",
        )
        self.assertEqual(cookie, "wps_sid=primary")

    def test_cookiecloud_pairs_sid_and_uid_with_same_path(self):
        cookie = daily.extract_cookiecloud_cookie(
            {
                "lingxi.wps.cn": [
                    {
                        "name": "wps_sid",
                        "value": "root-sid",
                        "domain": "lingxi.wps.cn",
                        "path": "/",
                    },
                    {
                        "name": "wps_sid",
                        "value": "app-sid",
                        "domain": "lingxi.wps.cn",
                        "path": "/lingxi",
                    },
                    {
                        "name": "uid",
                        "value": "app-uid",
                        "domain": "lingxi.wps.cn",
                        "path": "/lingxi",
                    },
                ]
            },
            label="主号",
        )
        self.assertEqual(cookie, "wps_sid=app-sid; uid=app-uid")

    def test_cookiecloud_missing_sid_is_explicit(self):
        with self.assertRaises(daily.CookieCloudError) as caught:
            daily.extract_cookiecloud_cookie(
                {"lingxi.wps.cn": [{"name": "uid", "value": "42"}]},
                label="主号",
            )
        self.assertIn("wps_sid", str(caught.exception))

    def test_cookiecloud_ignores_missing_or_structured_values(self):
        with self.assertRaises(daily.CookieCloudError):
            daily.extract_cookiecloud_cookie(
                {
                    "lingxi.wps.cn": [
                        {"name": "wps_sid", "value": None},
                        {"name": "uid", "value": {"nested": "secret"}},
                    ]
                },
                label="主号",
            )

    def test_cookiecloud_failure_does_not_leak_credentials(self):
        profile = daily.CookieCloudProfile(
            label="主号",
            url="https://cookie.example/api",
            uuid="secret-uuid",
            password="secret-password",
        )

        def failing_factory(_url, _uuid, _password):
            raise RuntimeError("secret-uuid secret-password https://cookie.example/api")

        accounts = daily.load_cookiecloud_accounts([profile], factory=failing_factory)
        self.assertEqual(len(accounts), 1)
        message = accounts[0].error
        self.assertTrue(message)
        self.assertNotIn("secret-uuid", message)
        self.assertNotIn("secret-password", message)
        self.assertNotIn("cookie.example", message)
        self.assertNotIn("secret-uuid", repr(profile))
        self.assertNotIn("secret-password", repr(profile))
        self.assertNotIn("cookie.example", repr(profile))

    def test_cookiecloud_failure_does_not_block_static_account(self):
        profile = daily.CookieCloudProfile(
            "云账号", "https://cookie.example", "uuid", "password"
        )
        with mock.patch.dict(
            os.environ,
            {
                "WPSLINGXI_COOKIES": "静态|wps_sid=static; uid=1",
                "WPSLINGXI_COOKIECLOUD_PROFILES": "",
                "WPSLINGXI_COOKIECLOUD_URL": "",
                "WPSLINGXI_COOKIECLOUD_UUID": "",
                "WPSLINGXI_COOKIECLOUD_PASSWORD": "",
            },
            clear=False,
        ):
            with mock.patch.object(
                daily,
                "parse_cookiecloud_profiles",
                return_value=[profile],
            ):
                accounts = daily.load_accounts(
                    cookiecloud_factory=lambda _url, _uuid, _password: (_ for _ in ()).throw(
                        RuntimeError("sensitive details")
                    )
                )
        self.assertEqual([item.label for item in accounts], ["静态", "云账号"])
        self.assertFalse(accounts[0].error)
        self.assertIn("RuntimeError", accounts[1].error)
        self.assertNotIn("sensitive details", accounts[1].error)

    def test_cookiecloud_invalid_profile_does_not_block_static_or_valid_profile(self):
        cloud_data = {
            "lingxi.wps.cn": [
                {"name": "wps_sid", "value": "cloud"},
                {"name": "uid", "value": "2"},
            ]
        }
        with mock.patch.dict(
            os.environ,
            {
                "WPSLINGXI_COOKIES": "静态|wps_sid=static; uid=1",
                "WPSLINGXI_COOKIECLOUD_PROFILES": (
                    "坏配置\n"
                    "云账号|https://cookie.example|uuid|password"
                ),
                "WPSLINGXI_COOKIECLOUD_URL": "",
                "WPSLINGXI_COOKIECLOUD_UUID": "",
                "WPSLINGXI_COOKIECLOUD_PASSWORD": "",
            },
            clear=False,
        ):
            accounts = daily.load_accounts(
                cookiecloud_factory=lambda _url, _uuid, _password: FakeCookieCloud(
                    cloud_data
                )
            )
        self.assertEqual([item.label for item in accounts], ["静态", "CookieCloud-1", "云账号"])
        self.assertIn("格式错误", accounts[1].error)
        self.assertEqual(accounts[2].cookie, "wps_sid=cloud; uid=2")

    def test_cookiecloud_invalid_ipv6_url_does_not_block_other_accounts(self):
        cloud_data = {
            "lingxi.wps.cn": [
                {"name": "wps_sid", "value": "cloud"},
                {"name": "uid", "value": "2"},
            ]
        }
        with mock.patch.dict(
            os.environ,
            {
                "WPSLINGXI_COOKIES": "静态|wps_sid=static; uid=1",
                "WPSLINGXI_COOKIECLOUD_PROFILES": (
                    "坏URL|https://[::1|uuid|password\n"
                    "云账号|https://cookie.example|uuid|password"
                ),
                "WPSLINGXI_COOKIECLOUD_URL": "",
                "WPSLINGXI_COOKIECLOUD_UUID": "",
                "WPSLINGXI_COOKIECLOUD_PASSWORD": "",
            },
            clear=False,
        ):
            accounts = daily.load_accounts(
                cookiecloud_factory=lambda _url, _uuid, _password: FakeCookieCloud(
                    cloud_data
                )
            )
        self.assertEqual([item.label for item in accounts], ["静态", "坏URL", "云账号"])
        self.assertIn("URL 无效", accounts[1].error)
        self.assertEqual(accounts[2].cookie, "wps_sid=cloud; uid=2")

    def test_cookiecloud_malformed_domain_key_is_ignored(self):
        cookie = daily.extract_cookiecloud_cookie(
            {
                "https://[::1": [{"name": "wps_sid", "value": "bad"}],
                "lingxi.wps.cn": [{"name": "wps_sid", "value": "good"}],
            },
            label="主号",
        )
        self.assertEqual(cookie, "wps_sid=good")

    def test_static_and_cookiecloud_accounts_merge_and_dedupe(self):
        cloud_data = {
            "lingxi.wps.cn": [
                {"name": "wps_sid", "value": "cloud"},
                {"name": "uid", "value": "2"},
            ]
        }
        profiles = [
            daily.CookieCloudProfile("云账号", "https://cookie.example", "u", "p"),
            daily.CookieCloudProfile("重复账号", "https://cookie.example", "u2", "p2"),
        ]
        with mock.patch.dict(
            os.environ,
            {
                "WPSLINGXI_COOKIES": "静态|wps_sid=cloud; uid=2",
                "WPSLINGXI_COOKIECLOUD_PROFILES": "",
                "WPSLINGXI_COOKIECLOUD_URL": "",
                "WPSLINGXI_COOKIECLOUD_UUID": "",
                "WPSLINGXI_COOKIECLOUD_PASSWORD": "",
            },
            clear=False,
        ):
            with mock.patch.object(
                daily,
                "parse_cookiecloud_profiles",
                return_value=profiles,
            ):
                accounts = daily.load_accounts(
                    cookiecloud_factory=lambda _url, _uuid, _password: FakeCookieCloud(
                        cloud_data
                    )
                )
        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0].label, "静态")

    def test_static_and_cookiecloud_dedupe_ignores_cookie_order(self):
        cloud_data = {
            "lingxi.wps.cn": [
                {"name": "uid", "value": "2"},
                {"name": "wps_sid", "value": "cloud"},
            ]
        }
        profiles = [
            daily.CookieCloudProfile("云账号", "https://cookie.example", "u", "p")
        ]
        with mock.patch.dict(
            os.environ,
            {
                "WPSLINGXI_COOKIES": "静态|wps_sid=cloud; uid=2",
                "WPSLINGXI_COOKIECLOUD_PROFILES": "",
                "WPSLINGXI_COOKIECLOUD_URL": "",
                "WPSLINGXI_COOKIECLOUD_UUID": "",
                "WPSLINGXI_COOKIECLOUD_PASSWORD": "",
            },
            clear=False,
        ):
            with mock.patch.object(
                daily,
                "parse_cookiecloud_profiles",
                return_value=profiles,
            ):
                accounts = daily.load_accounts(
                    cookiecloud_factory=lambda _url, _uuid, _password: FakeCookieCloud(
                        cloud_data
                    )
                )
        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0].label, "静态")

    def test_static_and_cookiecloud_dedupe_uses_wps_sid(self):
        cloud_data = {
            "lingxi.wps.cn": [
                {"name": "wps_sid", "value": "cloud"},
                {"name": "uid", "value": "different"},
            ]
        }
        profiles = [
            daily.CookieCloudProfile("云账号", "https://cookie.example", "u", "p")
        ]
        with mock.patch.dict(
            os.environ,
            {
                "WPSLINGXI_COOKIES": "静态|wps_sid=cloud; uid=2; extra=value",
                "WPSLINGXI_COOKIECLOUD_PROFILES": "",
                "WPSLINGXI_COOKIECLOUD_URL": "",
                "WPSLINGXI_COOKIECLOUD_UUID": "",
                "WPSLINGXI_COOKIECLOUD_PASSWORD": "",
            },
            clear=False,
        ):
            with mock.patch.object(
                daily,
                "parse_cookiecloud_profiles",
                return_value=profiles,
            ):
                accounts = daily.load_accounts(
                    cookiecloud_factory=lambda _url, _uuid, _password: FakeCookieCloud(
                        cloud_data
                    )
                )
        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0].label, "静态")

    def test_cookiecloud_empty_payload_is_explicit(self):
        profile = daily.CookieCloudProfile(
            "主号", "https://cookie.example", "uuid", "password"
        )
        accounts = daily.load_cookiecloud_accounts(
            [profile],
            factory=lambda _url, _uuid, _password: FakeCookieCloud(None),
        )
        self.assertEqual(len(accounts), 1)
        self.assertIn("cookie_data", accounts[0].error)

    def test_cookiecloud_timeout_is_bounded(self):
        profile = daily.CookieCloudProfile(
            "主号", "https://cookie.example", "uuid", "password"
        )
        with mock.patch.object(daily, "COOKIECLOUD_TIMEOUT", 0.05):
            started = time.monotonic()
            accounts = daily.load_cookiecloud_accounts(
                [profile],
                factory=lambda _url, _uuid, _password: SlowCookieCloud(),
            )
        self.assertLess(time.monotonic() - started, 0.18)
        self.assertEqual(len(accounts), 1)
        self.assertIn("超时", accounts[0].error)

    def test_full_checkin_uses_date_and_balance_readback(self):
        session = FakeSession(
            [
                FakeResponse({"result": "ok", "data": {"tasks": [task()]}}),
                FakeResponse({"result": "ok", "data": {"total_balance": 100}}),
                FakeResponse({"result": "ok", "data": {"reward_amount": 10}}),
                FakeResponse({"result": "ok", "data": {"tasks": [task("claimed")]}}),
                FakeResponse({"result": "ok", "data": {"total_balance": 110}}),
            ]
        )
        result = daily.run_account(account(), session=session)
        self.assertTrue(result.ok)
        self.assertEqual(result.outcome, "claimed")
        self.assertEqual(result.credit, 10)
        self.assertIn(f"date={daily.beijing_today()}", session.calls[2]["url"])
        self.assertEqual(session.calls[2]["json"], {})

    def test_already_claimed_is_done(self):
        session = FakeSession(
            [
                FakeResponse({"result": "ok", "data": {"tasks": [task("claimed")]}}),
            ]
        )
        result = daily.run_account(account(), session=session)
        self.assertTrue(result.ok)
        self.assertEqual(result.outcome, "done")
        self.assertEqual(len(session.calls), 1)

    def test_primary_auth_failure_falls_back_to_kdocs(self):
        session = FakeSession(
            [
                FakeResponse({"result": "UserUnauthorized"}, status_code=401),
                FakeResponse({"result": "ok", "data": {"tasks": [task("claimed")]}}),
            ]
        )
        result = daily.run_account(account(), session=session)
        self.assertTrue(result.ok)
        self.assertEqual(result.detail["base"], daily.FALLBACK_BASE)

    def test_primary_not_found_also_falls_back(self):
        session = FakeSession(
            [
                FakeResponse({"message": "not found"}, status_code=404),
                FakeResponse({"result": "ok", "data": {"tasks": [task("claimed")]}}),
            ]
        )
        result = daily.run_account(account(), session=session)
        self.assertTrue(result.ok)
        self.assertEqual(result.detail["base"], daily.FALLBACK_BASE)

    def test_post_success_requires_task_readback(self):
        session = FakeSession(
            [
                FakeResponse({"result": "ok", "data": {"tasks": [task()]}}),
                FakeResponse({"result": "ok", "data": {"total_balance": 100}}),
                FakeResponse({"result": "ok", "data": {"reward_amount": 10}}),
                FakeResponse({"result": "ok", "data": {"tasks": [task("claimable")]}}),
                FakeResponse({"result": "ok", "data": {"total_balance": 110}}),
            ]
        )
        with self.assertRaises(daily.ApiError):
            daily.run_account(account(), session=session)

    def test_balance_unchanged_is_done_not_claimed(self):
        session = FakeSession(
            [
                FakeResponse({"result": "ok", "data": {"tasks": [task()]}}),
                FakeResponse({"result": "ok", "data": {"total_balance": 100}}),
                FakeResponse({"result": "ok", "data": {"reward_amount": 10}}),
                FakeResponse({"result": "ok", "data": {"tasks": [task("claimed")]}}),
                FakeResponse({"result": "ok", "data": {"total_balance": 100}}),
            ]
        )
        result = daily.run_account(account(), session=session)
        self.assertTrue(result.ok)
        self.assertEqual(result.outcome, "done")
        self.assertEqual(result.credit, 0)

    def test_jsonl_has_no_cookie(self):
        result = daily.AccountResult(account(), True, "done", "ok", detail={"base": "x"})
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "result.jsonl")
            daily.append_jsonl(path, result)
            with open(path, encoding="utf-8") as handle:
                line = handle.readline()
        self.assertNotIn("wps_sid", line)
        self.assertEqual(json.loads(line)["provider"], "wps-lingxi")

    def test_jsonl_redacts_sensitive_detail(self):
        result = daily.AccountResult(
            account(),
            True,
            "done",
            "ok",
            detail={
                "task_before": {
                    "wps_sid": "secret-sid",
                    "uid": "secret-uid",
                    "status": "claimed",
                },
                "message": "token=secret-token",
            },
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "result.jsonl")
            daily.append_jsonl(path, result)
            with open(path, encoding="utf-8") as handle:
                line = handle.readline()
        self.assertNotIn("secret-sid", line)
        self.assertNotIn("secret-uid", line)
        self.assertNotIn("secret-token", line)
        payload = json.loads(line)
        self.assertEqual(payload["detail"]["task_before"]["status"], "claimed")

    def test_jsonl_redacts_structured_cookie_name_value(self):
        result = daily.AccountResult(
            account(),
            True,
            "done",
            "ok",
            detail={
                "cookies": [
                    {"name": "wps_sid", "value": "secret-sid"},
                    {"name": "Set-Cookie", "value": "session=secret-session"},
                ],
                "normal": {"name": "status", "value": "claimed"},
            },
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "result.jsonl")
            daily.append_jsonl(path, result)
            with open(path, encoding="utf-8") as handle:
                line = handle.readline()
        self.assertNotIn("secret-sid", line)
        self.assertNotIn("secret-session", line)
        payload = json.loads(line)
        self.assertEqual(payload["detail"]["normal"]["value"], "claimed")

    def test_push_exception_log_does_not_include_url(self):
        error = daily.requests.RequestException(
            "failed https://bark.example/private-token"
        )
        stderr = io.StringIO()
        with mock.patch.object(daily.requests, "post", side_effect=error):
            with contextlib.redirect_stderr(stderr):
                daily._post("https://bark.example/private-token")
        output = stderr.getvalue()
        self.assertNotIn("private-token", output)
        self.assertNotIn("bark.example", output)
        self.assertIn("RequestException", output)

    def test_sanitize_redacts_bearer_and_cookie_pairs(self):
        value = daily._sanitize(
            "Authorization: Bearer secret-token; Cookie: wps_sid=secret-sid; uid=42"
        )
        self.assertNotIn("secret-token", value)
        self.assertNotIn("secret-sid", value)
        self.assertNotIn("uid=42", value)

    def test_sanitize_redacts_entire_generic_cookie_header(self):
        value = daily._sanitize("Cookie: session=secret-a; csrf=secret-b")
        self.assertNotIn("secret-a", value)
        self.assertNotIn("secret-b", value)

    def test_sanitize_redacts_session_and_csrf_pairs(self):
        value = daily._sanitize("session=secret-session; csrf=secret-csrf")
        self.assertNotIn("secret-session", value)
        self.assertNotIn("secret-csrf", value)

    def test_sanitize_redacts_bare_url_and_uuid(self):
        value = daily._sanitize(
            "https://cookie.example/private 550e8400-e29b-41d4-a716-446655440000"
        )
        self.assertNotIn("cookie.example", value)
        self.assertNotIn("550e8400", value)

    def test_summary_redacts_account_label(self):
        result = daily.AccountResult(
            daily.Account("wps_sid=secret-sid|uid=42", "wps_sid=abc"),
            False,
            "failed",
            "Cookie: session=secret-cookie",
        )
        summary = daily.format_summary([result])
        self.assertNotIn("secret-sid", summary)
        self.assertNotIn("secret-cookie", summary)

    def test_summary_and_jsonl_redact_url_label(self):
        result = daily.AccountResult(
            daily.Account("https://cookie.example/private-uuid", "wps_sid=abc"),
            False,
            "failed",
            "failed",
        )
        summary = daily.format_summary([result])
        self.assertNotIn("cookie.example", summary)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "result.jsonl")
            daily.append_jsonl(path, result)
            with open(path, encoding="utf-8") as handle:
                line = handle.readline()
        self.assertNotIn("cookie.example", line)


if __name__ == "__main__":
    unittest.main()
