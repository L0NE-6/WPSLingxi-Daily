#!/usr/bin/env python3
"""WPS Lingxi Daily - multi-account daily check-in and balance verification."""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import queue
import re
import sys
import threading
import time
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

import requests

VERSION = "1.0.1"
PRIMARY_BASE = "https://lingxi.wps.cn"
FALLBACK_BASE = "https://lingxi.kdocs.cn"
TASKS_PATH = "/api/public/v1/tasks"
BALANCE_PATH = "/api/public/v1/credits/balance"
CHECKIN_KEY = "daily_check_in"
DEFAULT_TIMEOUT = 20
COOKIECLOUD_TIMEOUT = 30
BEIJING = timezone(timedelta(hours=8))

_SECRET_RE = re.compile(
    r"(?i)(cookie|wps_sid|authorization|token|uuid|password)(\s*[:=]\s*)([^\s;,]+)"
)
_AUTH_HEADER_RE = re.compile(
    r"(?i)\b(authorization|proxy-authorization)(\s*[:=]\s*)(?:bearer\s+)?[^\s,;]+"
)
_COOKIE_HEADER_RE = re.compile(r"(?i)\b(cookie|set-cookie)(\s*[:=]\s*)[^\r\n]+")
_COOKIE_PAIR_RE = re.compile(
    r"(?i)\b("
    r"api[_-]?key|access[_-]?token|refresh[_-]?token|wps_sid|uid|token|"
    r"uuid|password|key|session|csrf|jwt"
    r")=([^;\s&]+)"
)
_URL_RE = re.compile(r"(?i)\bhttps?://[^\s\"'<>]+")
_UUID_RE = re.compile(
    r"(?i)\b(?:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|[0-9a-f]{32})\b"
)
_SENSITIVE_KEY_RE = re.compile(
    r"(?i)(^|[_-])("
    r"cookie|wps_sid|authorization|token|uuid|password|secret|webhook|bark|"
    r"uid|session|csrf|jwt|api[_-]?key"
    r")($|[_-])"
)


class WpsError(Exception):
    pass


class NetworkError(WpsError):
    pass


class ProtocolError(WpsError):
    pass


class AuthError(WpsError):
    pass


class ApiError(WpsError):
    def __init__(
        self,
        message: str,
        *,
        status: Optional[int] = None,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code


class CookieCloudError(ValueError):
    pass


class CookieCloudDependencyError(CookieCloudError):
    pass


@dataclass(frozen=True)
class Account:
    label: str
    cookie: str
    error: str = ""


@dataclass(frozen=True)
class CookieCloudProfile:
    label: str
    url: str = field(repr=False)
    uuid: str = field(repr=False)
    password: str = field(repr=False)


@dataclass
class AccountResult:
    account: Account
    ok: bool
    outcome: str
    message: str
    credit: float = 0
    detail: Dict[str, Any] = field(default_factory=dict)


def _env(name: str) -> str:
    return (os.getenv(name) or "").strip()


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (LookupError, ValueError):
            pass


def _sanitize(text: Any, limit: int = 300) -> str:
    value = _COOKIE_HEADER_RE.sub(r"\1\2[redacted]", str(text))
    value = value.replace("\r", " ").replace("\n", " ").strip()
    value = _AUTH_HEADER_RE.sub(r"\1\2[redacted]", value)
    value = _SECRET_RE.sub(r"\1\2[redacted]", value)
    value = _COOKIE_PAIR_RE.sub(r"\1=[redacted]", value)
    value = _URL_RE.sub("[redacted-url]", value)
    value = _UUID_RE.sub("[redacted-uuid]", value)
    return value[:limit]


def _sanitize_label(label: Any) -> str:
    raw = str(label)
    if "://" in raw or re.search(r"(?i)\buuid\b", raw):
        return "[redacted-label]"
    return _sanitize(raw, limit=80)


def _sanitize_detail(value: Any) -> Any:
    if isinstance(value, dict):
        name = value.get("name")
        redact_value = isinstance(name, str) and bool(_SENSITIVE_KEY_RE.search(name))
        return {
            str(key): (
                "[redacted]"
                if _SENSITIVE_KEY_RE.search(str(key))
                or (redact_value and str(key).lower() == "value")
                else _sanitize_detail(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitize_detail(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_detail(item) for item in value]
    if isinstance(value, str):
        return _sanitize(value, limit=2000)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return _sanitize(value, limit=2000)


def _split_entries(raw: str) -> List[str]:
    if not raw:
        return []
    return [item.strip() for item in re.split(r"[\r\n&]+", raw) if item.strip()]


def _normalize_cookie(value: str) -> str:
    text = value.strip()
    if text.lower().startswith("cookie:"):
        text = text[7:].strip()
    if not text or len(text) > 8192 or any(ord(char) < 32 or ord(char) == 127 for char in text):
        raise ValueError("invalid cookie")
    if not re.search(r"(?i)(?:^|;\s*)wps_sid\s*=", text):
        if ";" in text:
            raise ValueError("cookie must contain wps_sid")
        text = "wps_sid=" + text
    return text


def parse_accounts(raw: str) -> List[Account]:
    accounts: List[Account] = []
    for index, entry in enumerate(_split_entries(raw), 1):
        if entry.startswith("#"):
            continue
        label = f"WPS-{index}"
        cookie = entry
        if "|" in entry:
            parts = [part.strip() for part in entry.split("|")]
            if len(parts) >= 3 and parts[1] and parts[2]:
                label = parts[0]
                cookie = f"wps_sid={parts[1]}; uid={parts[2]}"
            elif len(parts) == 2:
                label, cookie = parts[0], parts[1]
        try:
            cookie = _normalize_cookie(cookie)
        except ValueError as exc:
            raise ValueError(f"{label}: {exc}") from exc
        accounts.append(Account(label or f"WPS-{index}", cookie))
    return accounts


def parse_cookiecloud_profiles(
    raw: Optional[str] = None,
    *,
    errors: Optional[List[Tuple[str, str]]] = None,
) -> List[CookieCloudProfile]:
    profiles: List[CookieCloudProfile] = []
    text = _env("WPSLINGXI_COOKIECLOUD_PROFILES") if raw is None else raw

    def report(label: str, message: str) -> None:
        if errors is None:
            raise CookieCloudError(message)
        errors.append((label, message))

    for index, line in enumerate(text.splitlines(), 1):
        entry = line.strip()
        if not entry or entry.startswith("#"):
            continue
        parts = [part.strip() for part in entry.split("|", 3)]
        if len(parts) != 4 or not all(parts):
            report(
                f"CookieCloud-{index}",
                f"CookieCloud 第 {index} 行格式错误，应为 备注|URL|UUID|密码",
            )
            continue
        label, url, uuid, password = parts
        try:
            parsed = urllib.parse.urlsplit(url)
        except ValueError:
            report(label, f"{label}: CookieCloud URL 无效")
            continue
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            report(label, f"{label}: CookieCloud URL 无效")
            continue
        if parsed.username or parsed.password:
            report(label, f"{label}: CookieCloud URL 不能包含内嵌凭据")
            continue
        profiles.append(
            CookieCloudProfile(label=label, url=url, uuid=uuid, password=password)
        )

    if raw is None:
        single = {
            "url": _env("WPSLINGXI_COOKIECLOUD_URL"),
            "uuid": _env("WPSLINGXI_COOKIECLOUD_UUID"),
            "password": _env("WPSLINGXI_COOKIECLOUD_PASSWORD"),
        }
        configured = [bool(value) for value in single.values()]
        if any(configured) and not all(configured):
            report(
                "CookieCloud",
                "CookieCloud 单账号配置不完整，需要同时设置 URL、UUID 和 PASSWORD",
            )
        elif all(configured):
            try:
                parsed = urllib.parse.urlsplit(single["url"])
            except ValueError:
                report("CookieCloud", "CookieCloud URL 无效")
                parsed = None
            if parsed is not None and (
                parsed.scheme not in ("http", "https") or not parsed.netloc
            ):
                report("CookieCloud", "CookieCloud URL 无效")
            elif parsed is not None and (parsed.username or parsed.password):
                report("CookieCloud", "CookieCloud URL 不能包含内嵌凭据")
            elif parsed is not None:
                profiles.append(
                    CookieCloudProfile(
                        label="CookieCloud",
                        url=single["url"],
                        uuid=single["uuid"],
                        password=single["password"],
                    )
                )
    return profiles


def _default_cookiecloud_factory(url: str, uuid: str, password: str) -> Any:
    try:
        from PyCookieCloud import PyCookieCloud
    except ImportError as exc:
        raise CookieCloudDependencyError(
            "未安装 PyCookieCloud，请先执行 pip install -r requirements.txt"
        ) from exc
    return PyCookieCloud(url, uuid, password)


def _cookiecloud_domain_score(domain: str) -> int:
    value = domain.strip().lower()
    if "://" in value:
        try:
            host = urllib.parse.urlsplit(value).hostname or ""
        except ValueError:
            return 0
    else:
        host = value.lstrip(".").split("/", 1)[0].split(":", 1)[0]
    if host == "lingxi.wps.cn":
        return 100
    if host == "wps.cn":
        return 90
    if host.endswith(".wps.cn"):
        return 80
    if host == "lingxi.kdocs.cn":
        return 70
    if host == "kdocs.cn":
        return 60
    if host.endswith(".kdocs.cn"):
        return 50
    return 0


def _safe_cookie_value(value: Any) -> Optional[str]:
    if value is None or isinstance(value, (dict, list, tuple)):
        return None
    text = str(value)
    if not text or len(text) > 4096:
        return None
    if any(ord(char) < 32 or ord(char) == 127 or char == ";" for char in text):
        return None
    return text


def _fetch_cookiecloud_data(client: Any) -> Any:
    result: queue.Queue[Any] = queue.Queue(maxsize=1)

    def worker() -> None:
        try:
            result.put(("ok", client.get_decrypted_data()))
        except Exception as exc:
            result.put(("error", exc))

    thread = threading.Thread(target=worker, name="cookiecloud-fetch", daemon=True)
    thread.start()
    try:
        status, payload = result.get(timeout=COOKIECLOUD_TIMEOUT)
    except queue.Empty:
        raise CookieCloudError(
            f"CookieCloud 拉取超时（超过 {COOKIECLOUD_TIMEOUT} 秒）"
        ) from None
    if status == "error":
        raise payload
    return payload


def extract_cookiecloud_cookie(
    cookie_data: Mapping[str, Any],
    *,
    label: str,
) -> str:
    domains = sorted(
        (
            (domain, _cookiecloud_domain_score(domain))
            for domain in cookie_data
            if isinstance(domain, str)
        ),
        key=lambda item: (-item[1], item[0].lower()),
    )
    for domain, score in domains:
        if score <= 0:
            continue
        items = cookie_data.get(domain)
        if not isinstance(items, list):
            continue
        groups: Dict[Tuple[str, str], Dict[str, str]] = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").lower()
            if name not in ("wps_sid", "uid"):
                continue
            value = _safe_cookie_value(item.get("value"))
            if not value:
                continue
            item_domain = str(item.get("domain") or domain).strip().lower()
            item_path = str(item.get("path") or "/").strip() or "/"
            groups.setdefault((item_domain, item_path), {})[name] = value
        candidates = [
            (group, values)
            for group, values in groups.items()
            if "wps_sid" in values
        ]
        candidates.sort(
            key=lambda item: (
                0 if "uid" in item[1] else 1,
                0 if item[0][1] == "/" else 1,
                0
                if item[0][0].lstrip(".") == domain.lstrip(".").lower()
                else 1,
                len(item[0][1]),
                item[0][0],
                item[0][1],
            )
        )
        if candidates:
            values = candidates[0][1]
            cookie = f"wps_sid={values['wps_sid']}"
            if "uid" in values:
                cookie += f"; uid={values['uid']}"
            return cookie
    raise CookieCloudError(f"{label}: CookieCloud 中没有可用的 wps_sid")


def load_cookiecloud_accounts(
    profiles: Optional[Sequence[CookieCloudProfile]] = None,
    *,
    factory: Optional[Callable[[str, str, str], Any]] = None,
) -> List[Account]:
    parse_errors: List[Tuple[str, str]] = []
    profiles = (
        list(profiles)
        if profiles is not None
        else parse_cookiecloud_profiles(errors=parse_errors)
    )
    accounts: List[Account] = [
        Account(label=_sanitize_label(label), cookie="", error=_sanitize(message))
        for label, message in parse_errors
    ]
    if not profiles:
        return accounts
    client_factory = factory or _default_cookiecloud_factory
    for profile in profiles:
        safe_label = _sanitize_label(profile.label)
        try:
            client = client_factory(profile.url, profile.uuid, profile.password)
            cookie_data = _fetch_cookiecloud_data(client)
        except CookieCloudDependencyError as exc:
            accounts.append(
                Account(label=safe_label, cookie="", error=_sanitize(exc))
            )
            continue
        except CookieCloudError as exc:
            accounts.append(
                Account(label=safe_label, cookie="", error=_sanitize(exc))
            )
            continue
        except Exception as exc:
            accounts.append(
                Account(
                    label=safe_label,
                    cookie="",
                    error=(
                        f"{safe_label}: CookieCloud 拉取或解密失败"
                        f"（{type(exc).__name__}）"
                    ),
                )
            )
            continue
        if not isinstance(cookie_data, dict):
            accounts.append(
                Account(
                    label=safe_label,
                    cookie="",
                    error=f"{safe_label}: CookieCloud 未返回可用的 cookie_data",
                )
            )
            continue
        try:
            cookie = extract_cookiecloud_cookie(cookie_data, label=safe_label)
        except CookieCloudError as exc:
            accounts.append(
                Account(
                    label=safe_label,
                    cookie="",
                    error=_sanitize(exc),
                )
            )
            continue
        accounts.append(Account(label=profile.label, cookie=cookie))
    return accounts


def _account_identity(account: Account) -> str:
    for part in account.cookie.split(";"):
        name, separator, value = part.strip().partition("=")
        if separator and name.strip().lower() == "wps_sid" and value.strip():
            return "wps_sid=" + value.strip()
    return account.cookie


def load_accounts(
    *,
    cookiecloud_factory: Optional[Callable[[str, str, str], Any]] = None,
) -> List[Account]:
    raw = _env("WPSLINGXI_COOKIES") or _env("WPSLINGXI_COOKIE")
    accounts = parse_accounts(raw) if raw else []
    accounts.extend(load_cookiecloud_accounts(factory=cookiecloud_factory))

    unique: List[Account] = []
    seen = set()
    for account in accounts:
        if account.error:
            unique.append(account)
            continue
        identity = _account_identity(account)
        if identity in seen:
            continue
        seen.add(identity)
        unique.append(account)
    return unique


def make_session(account: Account) -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "Cookie": account.cookie,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        }
    )
    return session


def _message(payload: Any) -> str:
    if isinstance(payload, dict):
        for key in ("hint", "message", "msg", "error", "result"):
            value = payload.get(key)
            if value:
                return _sanitize(value)
    return ""


def request_json(
    session: requests.Session,
    base: str,
    method: str,
    path: str,
    *,
    body: Optional[Dict[str, Any]] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> Dict[str, Any]:
    try:
        response = session.request(method, base + path, json=body, timeout=timeout)
    except requests.RequestException as exc:
        raise NetworkError(_sanitize(f"网络请求失败：{exc}")) from exc
    try:
        payload = response.json()
    except ValueError as exc:
        raise ProtocolError(f"服务端返回非 JSON（HTTP {response.status_code}）") from exc
    if not isinstance(payload, dict):
        raise ProtocolError("服务端响应不是对象")
    if response.status_code in (401, 403) or payload.get("result") == "UserUnauthorized":
        raise AuthError(_sanitize(_message(payload) or "WPS 登录态已失效"))
    if not 200 <= response.status_code < 300:
        raise ApiError(
            _sanitize(f"HTTP {response.status_code}：{_message(payload) or '请求失败'}"),
            status=response.status_code,
            code=str(payload.get("code") or ""),
        )
    return payload


def _data(payload: Dict[str, Any]) -> Any:
    return payload.get("data") if "data" in payload else payload


def list_tasks(session: requests.Session, base: str) -> List[Dict[str, Any]]:
    payload = request_json(session, base, "GET", TASKS_PATH)
    data = _data(payload)
    tasks = data.get("tasks") if isinstance(data, dict) else None
    if not isinstance(tasks, list):
        raise ProtocolError("任务中心缺少 data.tasks")
    return [task for task in tasks if isinstance(task, dict)]


def find_daily(tasks: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    for task in tasks:
        if str(task.get("task_key") or "") == CHECKIN_KEY:
            return task
    raise ProtocolError("任务中心没有 daily_check_in")


def task_claimed(task: Dict[str, Any]) -> bool:
    return str(task.get("status") or "").lower() in ("claimed", "completed", "complete", "done")


def beijing_today() -> str:
    return datetime.now(timezone.utc).astimezone(BEIJING).strftime("%Y-%m-%d")


def claim_date(task: Dict[str, Any], today: Optional[str] = None) -> str:
    today = today or beijing_today()
    extra = task.get("extra") if isinstance(task.get("extra"), dict) else {}
    days = extra.get("check_in_days")
    if isinstance(days, list):
        for item in days:
            if isinstance(item, dict) and item.get("date") == today:
                return today
        for item in days:
            if isinstance(item, dict) and item.get("status") == "available" and item.get("date"):
                return str(item["date"])
    return today


def get_balance(session: requests.Session, base: str) -> float:
    payload = request_json(session, base, "GET", BALANCE_PATH)
    data = _data(payload)
    if not isinstance(data, dict):
        raise ProtocolError("余额接口缺少 data")
    for key in ("total_balance", "balance"):
        try:
            value = float(data.get(key))
            if value >= 0:
                return value
        except (TypeError, ValueError):
            continue
    raise ProtocolError("余额接口缺少有效 total_balance/balance")


def claim_daily(
    session: requests.Session,
    base: str,
    date: str,
) -> Dict[str, Any]:
    path = f"/api/public/v1/tasks/{CHECKIN_KEY}/claim?date={urllib.parse.quote(date)}"
    payload = request_json(session, base, "POST", path, body={})
    result = payload.get("result")
    if result and result != "ok":
        raise ApiError(_sanitize(payload.get("hint") or _message(payload) or f"签到失败：{result}"))
    return payload


def _run_on_base(account: Account, session: requests.Session, base: str) -> AccountResult:
    tasks_before = list_tasks(session, base)
    daily_before = find_daily(tasks_before)
    if task_claimed(daily_before):
        return AccountResult(
            account=account,
            ok=True,
            outcome="done",
            message="服务端确认今日已签到",
            detail={"base": base, "task": daily_before},
        )

    before_balance = get_balance(session, base)
    date = claim_date(daily_before)
    claim_payload = claim_daily(session, base, date)

    tasks_after = list_tasks(session, base)
    daily_after = find_daily(tasks_after)
    after_balance = get_balance(session, base)
    if not task_claimed(daily_after):
        raise ApiError("签到提交后，任务回读仍不是 claimed")

    delta = after_balance - before_balance
    if delta > 0:
        outcome = "claimed"
        message = f"服务端确认签到，余额 +{delta:g}"
    else:
        outcome = "done"
        message = "服务端确认今日已签到，余额未变化"
    return AccountResult(
        account=account,
        ok=True,
        outcome=outcome,
        message=message,
        credit=delta if delta > 0 else 0,
        detail={
            "base": base,
            "date": date,
            "task_before": daily_before,
            "task_after": daily_after,
            "balance_before": before_balance,
            "balance_after": after_balance,
            "claim_result": claim_payload.get("result"),
        },
    )


def run_account(
    account: Account,
    *,
    session: Optional[requests.Session] = None,
) -> AccountResult:
    if account.error:
        raise AuthError(account.error)
    owns_session = session is None
    session = session or make_session(account)
    try:
        last_error: Optional[WpsError] = None
        for base in (PRIMARY_BASE, FALLBACK_BASE):
            try:
                return _run_on_base(account, session, base)
            except (AuthError, ApiError) as exc:
                if isinstance(exc, ApiError) and exc.status not in (401, 403, 404):
                    raise
                last_error = exc
                continue
        raise last_error or AuthError("WPS 登录态已失效")
    finally:
        if owns_session:
            session.close()


def append_jsonl(path: str, result: AccountResult) -> None:
    if not path:
        return
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "provider": "wps-lingxi",
        "label": _sanitize_label(result.account.label),
        "outcome": result.outcome,
        "ok": result.ok,
        "credit": result.credit,
        "message": _sanitize(result.message),
        "detail": _sanitize_detail(result.detail),
    }
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def format_summary(results: Sequence[AccountResult]) -> str:
    lines = [f"🟦 WPS Lingxi Daily v{VERSION}", f"账号数: {len(results)}"]
    for result in results:
        icon = "✅" if result.ok else "❌"
        label = _sanitize_label(result.account.label)
        message = _sanitize(result.message)
        lines.append(
            f"{icon} {label} · {result.outcome} · "
            f"{message} · credit={result.credit:g}"
        )
    lines.append(f"结果: {sum(1 for item in results if item.ok)}/{len(results)} 成功")
    return "\n".join(lines)


def _notify_enabled(results: Sequence[AccountResult]) -> bool:
    mode = _env("WPSLINGXI_NOTIFY").lower()
    if mode in ("0", "off", "false", "none"):
        return False
    if mode in ("fail", "failure", "failed"):
        return any(not result.ok for result in results)
    return True


def _post(url: str, **kwargs: Any) -> None:
    try:
        response = requests.post(url, timeout=DEFAULT_TIMEOUT, **kwargs)
        if response.status_code >= 400:
            print(f"⚠️ 推送失败 HTTP {response.status_code}", file=sys.stderr)
    except requests.RequestException as exc:
        print(f"⚠️ 推送异常：{type(exc).__name__}", file=sys.stderr)


def notify(text: str, results: Sequence[AccountResult]) -> None:
    if not _notify_enabled(results):
        return
    title = "WPS Lingxi Daily 签到报告"
    pushplus = _env("PUSHPLUS_TOKEN")
    if pushplus:
        _post(
            "https://www.pushplus.plus/send",
            json={"token": pushplus, "title": title, "content": text, "template": "markdown"},
        )
    bark = _env("BARK_URL")
    if bark:
        _post(bark.rstrip("/"), json={"title": title, "body": text})
    serverchan = _env("SERVERCHAN_SENDKEY")
    if serverchan:
        _post(f"https://sctapi.ftqq.com/{serverchan}.send", data={"title": title, "desp": text})
    wxpusher = _env("WXPUSHER_APP_TOKEN")
    wx_uids = [item.strip() for item in re.split(r"[,;]", _env("WXPUSHER_UID")) if item.strip()]
    if wxpusher and wx_uids:
        _post(
            "https://wxpusher.zjiecode.com/api/send/message",
            json={
                "appToken": wxpusher,
                "content": text,
                "summary": title,
                "contentType": 1,
                "uids": wx_uids,
            },
        )
    wecom = _env("WECOM_WEBHOOK")
    if wecom:
        _post(wecom, json={"msgtype": "markdown", "markdown": {"content": text}})
    dingtalk = _env("DINGTALK_WEBHOOK")
    if dingtalk:
        secret = _env("DINGTALK_SECRET")
        url = dingtalk
        if secret:
            timestamp = str(int(time.time() * 1000))
            string_to_sign = f"{timestamp}\n{secret}"
            sign = base64.b64encode(
                hmac.new(secret.encode(), string_to_sign.encode(), hashlib.sha256).digest()
            ).decode()
            separator = "&" if "?" in url else "?"
            url += f"{separator}timestamp={timestamp}&sign={urllib.parse.quote(sign)}"
        _post(url, json={"msgtype": "markdown", "markdown": {"title": title, "text": text}})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="WPS Lingxi multi-account daily check-in")
    parser.add_argument("--only", type=int, default=0, help="only run the 1-based account index")
    parser.add_argument("--no-notify", action="store_true")
    parser.add_argument(
        "--jsonl",
        default=os.getenv("WPSLINGXI_JSONL") or "wpslingxi_results.jsonl",
        help="append one JSON object per account",
    )
    parser.add_argument("--version", action="version", version=VERSION)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    _configure_stdio()
    args = build_parser().parse_args(argv)
    try:
        accounts = load_accounts()
    except ValueError as exc:
        print(f"❌ 账号配置错误：{_sanitize(exc)}", file=sys.stderr)
        return 2
    if args.only:
        if args.only < 1 or args.only > len(accounts):
            print(f"❌ --only 超出范围：{args.only}", file=sys.stderr)
            return 2
        accounts = [accounts[args.only - 1]]
    if not accounts:
        print(
            "❌ 未配置静态 Cookie 或 WPSLINGXI_COOKIECLOUD_*",
            file=sys.stderr,
        )
        return 2

    results: List[AccountResult] = []
    for account in accounts:
        if account.error:
            result = AccountResult(
                account=account,
                ok=False,
                outcome="failed",
                message=_sanitize(account.error),
            )
        else:
            try:
                result = run_account(account)
            except Exception as exc:
                result = AccountResult(
                    account=account,
                    ok=False,
                    outcome="failed",
                    message=_sanitize(exc),
                )
        results.append(result)
        append_jsonl(args.jsonl, result)

    summary = format_summary(results)
    print("\n" + summary)
    if not args.no_notify:
        notify(summary, results)
    return 0 if all(result.ok for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
