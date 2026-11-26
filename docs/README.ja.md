# 🟦 WPS Lingxi Daily

[简体中文](../README.md) · [English](README.en.md) · [繁體中文](README.zh-Hant.md) · **日本語** · [한국어](README.ko.md) · [Português (BR)](README.pt-BR.md)
> バージョン：**v1.0.1**（2026-11-26）

単一 Python ファイルで動かす WPS Lingxi の複数アカウント毎日チェックイン。

## アカウント形式

```bash
export WPSLINGXI_COOKIES='メイン|wps_sid_value|123456'
python3 wpslingxi_daily.py
```

`ラベル|wps_sid|uid` または完全な `wps_sid=...; uid=...` Cookie を使用できます。

## CookieCloud

単一アカウントでは `WPSLINGXI_COOKIECLOUD_URL`、`WPSLINGXI_COOKIECLOUD_UUID`、
`WPSLINGXI_COOKIECLOUD_PASSWORD` を使用します。複数アカウントでは
`WPSLINGXI_COOKIECLOUD_PROFILES` に `ラベル|URL|UUID|パスワード` を 1 行ずつ設定します。

静的 Cookie が優先され、`wps_sid` で重複アカウントを削除します。
`wps_sid` と任意の `uid` は同じ WPS ドメインから取得します。1 つの設定が
失敗しても他のアカウントは継続し、各取得は 30 秒で打ち切ります。

## 成功判定

`/api/public/v1/tasks` で `daily_check_in` を探し、残高を読み、日付付きで claim し、タスクと残高を再読込します。claim リクエストの成功だけでは完了にしません。

## デプロイ

Qinglong: `pip3 install -r requirements.txt && task wpslingxi_daily.py`

GitHub Actions: 静的 Cookie、単一アカウント用 3 Secrets、または複数
アカウント用 profiles Secret を登録します。`PyCookieCloud==1.0.4` は
`requirements.txt` から導入されます。

## セキュリティ

Cookie、`wps_sid`、uid、CookieCloud UUID、パスワード、認証情報を含むログを Git、Issue、公開スクリーンショットへ投稿しないでください。

利用範囲は [NOTICE.md](../NOTICE.md) を参照してください。

<p align="center">
  <img src="../assets/donate-wechat.png" width="240" alt="WeChat 投げ銭 QR" />
  &nbsp;&nbsp;
  <img src="../assets/donate-alipay.jpg" width="240" alt="Alipay 投げ銭 QR" />
</p>
