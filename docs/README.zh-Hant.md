# 🟦 WPS Lingxi Daily

[简体中文](../README.md) · [English](README.en.md) · [繁體中文](README.zh-Hant.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Português (BR)](README.pt-BR.md)

多帳號 WPS 靈犀每日簽到，單檔 Python。

## 帳號格式

```bash
export WPSLINGXI_COOKIES='主號|wps_sid_value|123456'
python3 wpslingxi_daily.py
```

支援 `備註|wps_sid|uid` 或完整 `wps_sid=...; uid=...` Cookie。

## 驗收

在 `/api/public/v1/tasks` 找到 `daily_check_in`，讀取餘額，按日期 claim，再回讀任務與餘額。只有 claim 請求成功不算完成。

## 部署

青龍：`pip3 install -r requirements.txt && task wpslingxi_daily.py`

GitHub Actions：加入 `WPSLINGXI_COOKIES` 或 `WPSLINGXI_COOKIE` Secrets。

## 安全

不要把 Cookie、`wps_sid`、uid 或含憑據的日誌提交到倉庫、Issue 或公開截圖。

完整規則見 [NOTICE.md](../NOTICE.md)。

<p align="center">
  <img src="../assets/donate-wechat.png" width="240" alt="微信讚賞碼" />
  &nbsp;&nbsp;
  <img src="../assets/donate-alipay.jpg" width="240" alt="支付寶收款碼" />
</p>
