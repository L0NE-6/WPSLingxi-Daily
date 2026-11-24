import json
import os
import tempfile
import unittest

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


if __name__ == "__main__":
    unittest.main()
