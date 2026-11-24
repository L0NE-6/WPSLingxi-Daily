# 🟦 WPS Lingxi Daily

[简体中文](../README.md) · [English](README.en.md) · [繁體中文](README.zh-Hant.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Português (BR)](README.pt-BR.md)

単一 Python ファイルで動かす WPS Lingxi の複数アカウント毎日チェックイン。

## アカウント形式

```bash
export WPSLINGXI_COOKIES='メイン|wps_sid_value|123456'
python3 wpslingxi_daily.py
```

`ラベル|wps_sid|uid` または完全な `wps_sid=...; uid=...` Cookie を使用できます。

## 成功判定

`/api/public/v1/tasks` で `daily_check_in` を探し、残高を読み、日付付きで claim し、タスクと残高を再読込します。claim リクエストの成功だけでは完了にしません。

## デプロイ

Qinglong: `pip3 install -r requirements.txt && task wpslingxi_daily.py`

GitHub Actions: `WPSLINGXI_COOKIES` または `WPSLINGXI_COOKIE` を Secrets に登録します。

## セキュリティ

Cookie、`wps_sid`、uid、認証情報を含むログを Git、Issue、公開スクリーンショットへ投稿しないでください。

利用範囲は [NOTICE.md](../NOTICE.md) を参照してください。

<p align="center">
  <img src="../assets/donate-wechat.png" width="240" alt="WeChat 投げ銭 QR" />
  &nbsp;&nbsp;
  <img src="../assets/donate-alipay.jpg" width="240" alt="Alipay 投げ銭 QR" />
</p>
