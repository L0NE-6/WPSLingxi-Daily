# 🟦 WPS Lingxi Daily
[简体中文](../README.md) · **English** · [繁體中文](README.zh-Hant.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Português (BR)](README.pt-BR.md)
> Version: **v1.0.0** (2026-11-24)


Multi-account WPS Lingxi daily check-in in one Python file.

## Account format

```bash
export WPSLINGXI_COOKIES='main|wps_sid_value|123456'
python3 wpslingxi_daily.py
```

Use `label|wps_sid|uid` or a full `wps_sid=...; uid=...` cookie.

## Success contract

The script finds `daily_check_in` in `/api/public/v1/tasks`, reads the balance, claims the date-specific task, then re-reads both tasks and balance. A successful claim request alone is not enough.

## Deployment

Qinglong: `pip3 install -r requirements.txt && task wpslingxi_daily.py`

GitHub Actions: add `WPSLINGXI_COOKIES` or `WPSLINGXI_COOKIE` to repository Secrets.

## Tests

```bash
python -m unittest discover -s tests -v
python -m compileall -q wpslingxi_daily.py tests
```

## Security

Never commit cookies, `wps_sid`, UIDs, or credential-bearing logs.

See [NOTICE.md](../NOTICE.md) for the usage policy.

<p align="center">
  <img src="../assets/donate-wechat.png" width="240" alt="WeChat tip QR" />
  &nbsp;&nbsp;
  <img src="../assets/donate-alipay.jpg" width="240" alt="Alipay tip QR" />
</p>
