# 🟦 WPS Lingxi Daily

[简体中文](../README.md) · [English](README.en.md) · **繁體中文** · [日本語](README.ja.md) · [한국어](README.ko.md) · [Português (BR)](README.pt-BR.md)
> 版本：**v1.0.1**（2026-11-26）

多帳號 WPS 靈犀每日簽到，單檔 Python。

## 帳號格式

```bash
export WPSLINGXI_COOKIES='主號|wps_sid_value|123456'
python3 wpslingxi_daily.py
```

支援 `備註|wps_sid|uid` 或完整 `wps_sid=...; uid=...` Cookie。

## CookieCloud

單帳號使用 `WPSLINGXI_COOKIECLOUD_URL`、`WPSLINGXI_COOKIECLOUD_UUID`、
`WPSLINGXI_COOKIECLOUD_PASSWORD`。多帳號使用
`WPSLINGXI_COOKIECLOUD_PROFILES`，每行 `備註|URL|UUID|密碼`。

靜態 Cookie 優先，並按 `wps_sid` 去重；`wps_sid` 與可選 `uid` 必須來自同一
WPS 網域。單一設定失敗不影響其他帳號，單次拉取上限 30 秒。

## 驗收

在 `/api/public/v1/tasks` 找到 `daily_check_in`，讀取餘額，按日期 claim，再回讀任務與餘額。只有 claim 請求成功不算完成。

## 部署

青龍：`pip3 install -r requirements.txt && task wpslingxi_daily.py`

GitHub Actions：加入靜態 Cookie、單帳號三個 CookieCloud Secrets，或多帳號
profiles Secret。工作流會從 `requirements.txt` 安裝 `PyCookieCloud==1.0.4`。

## 安全

不要把 Cookie、`wps_sid`、uid、CookieCloud UUID、密碼或含憑據的日誌提交到倉庫、Issue 或公開截圖。

完整規則見 [NOTICE.md](../NOTICE.md)。

<p align="center">
  <img src="../assets/donate-wechat.png" width="240" alt="微信讚賞碼" />
  &nbsp;&nbsp;
  <img src="../assets/donate-alipay.jpg" width="240" alt="支付寶收款碼" />
</p>
