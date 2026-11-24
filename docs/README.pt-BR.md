# 🟦 WPS Lingxi Daily

[简体中文](../README.md) · [English](README.en.md) · [繁體中文](README.zh-Hant.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · **Português (BR)**
> Versão: **v1.0.0** (2026-11-24)

Check-in diário do WPS Lingxi para várias contas em um único arquivo Python.

## Formato da conta

```bash
export WPSLINGXI_COOKIES='principal|wps_sid_value|123456'
python3 wpslingxi_daily.py
```

Use `rótulo|wps_sid|uid` ou um Cookie completo `wps_sid=...; uid=...`.

## Critério de sucesso

O script encontra `daily_check_in` em `/api/public/v1/tasks`, lê o saldo, faz o claim com a data e relê tarefas e saldo. O sucesso do pedido de claim não basta.

## Implantação

Qinglong: `pip3 install -r requirements.txt && task wpslingxi_daily.py`

GitHub Actions: adicione `WPSLINGXI_COOKIES` ou `WPSLINGXI_COOKIE` aos Secrets.

## Segurança

Não envie cookies, `wps_sid`, UIDs ou logs com credenciais para Git, Issues ou capturas públicas.

Consulte [NOTICE.md](../NOTICE.md) para a política de uso.

<p align="center">
  <img src="../assets/donate-wechat.png" width="240" alt="QR de gorjeta WeChat" />
  &nbsp;&nbsp;
  <img src="../assets/donate-alipay.jpg" width="240" alt="QR de gorjeta Alipay" />
</p>
