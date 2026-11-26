# 🟦 WPS Lingxi Daily
[简体中文](../README.md) · **English** · [繁體中文](README.zh-Hant.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Português (BR)](README.pt-BR.md)
> Version: **v1.0.1** (2026-11-26)


Multi-account WPS Lingxi daily check-in in one Python file.

## Account format

```bash
export WPSLINGXI_COOKIES='main|wps_sid_value|123456'
python3 wpslingxi_daily.py
```

Use `label|wps_sid|uid` or a full `wps_sid=...; uid=...` cookie.

## CookieCloud

Single account:

```text
WPSLINGXI_COOKIECLOUD_URL=https://cookie.example
WPSLINGXI_COOKIECLOUD_UUID=your-uuid
WPSLINGXI_COOKIECLOUD_PASSWORD=your-password
```

Multiple accounts use `WPSLINGXI_COOKIECLOUD_PROFILES`, one
`label|URL|UUID|password` entry per line. Static cookies take priority and
duplicate accounts are removed by `wps_sid`. Only `wps_sid` and optional `uid`
from the same WPS domain are paired. A failed profile does not block other
accounts, and each fetch is limited to 30 seconds.

## Success contract

The script finds `daily_check_in` in `/api/public/v1/tasks`, reads the balance, claims the date-specific task, then re-reads both tasks and balance. A successful claim request alone is not enough.

## Deployment

Qinglong: `pip3 install -r requirements.txt && task wpslingxi_daily.py`

GitHub Actions: add static cookies, either three single-account CookieCloud
Secrets or the one multi-account profiles Secret. The workflow installs
`PyCookieCloud==1.0.4` from `requirements.txt`.

## Tests

```bash
python -m unittest discover -s tests -v
python -m compileall -q wpslingxi_daily.py tests
```

The CI test matrix runs on Python 3.8 and 3.11.

## Security

Never commit cookies, `wps_sid`, UIDs, CookieCloud UUIDs, passwords, or
credential-bearing logs.

See [NOTICE.md](../NOTICE.md) for the usage policy.

<p align="center">
  <img src="../assets/donate-wechat.png" width="240" alt="WeChat tip QR" />
  &nbsp;&nbsp;
  <img src="../assets/donate-alipay.jpg" width="240" alt="Alipay tip QR" />
</p>
