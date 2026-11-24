# 🟦 WPS Lingxi Daily

[简体中文](../README.md) · [English](README.en.md) · [繁體中文](README.zh-Hant.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Português (BR)](README.pt-BR.md)

단일 Python 파일로 실행하는 WPS Lingxi 다중 계정 일일 체크인.

## 계정 형식

```bash
export WPSLINGXI_COOKIES='메인|wps_sid_value|123456'
python3 wpslingxi_daily.py
```

`라벨|wps_sid|uid` 또는 전체 `wps_sid=...; uid=...` Cookie를 사용할 수 있습니다.

## 성공 판정

`/api/public/v1/tasks`에서 `daily_check_in`을 찾고 잔액을 읽은 뒤 날짜를 붙여 claim하고, 작업과 잔액을 다시 읽습니다. claim 요청 성공만으로 완료 처리하지 않습니다.

## 배포

Qinglong: `pip3 install -r requirements.txt && task wpslingxi_daily.py`

GitHub Actions: `WPSLINGXI_COOKIES` 또는 `WPSLINGXI_COOKIE`를 Secrets에 추가합니다.

## 보안

Cookie, `wps_sid`, uid 또는 자격 증명이 포함된 로그를 Git, Issue, 공개 스크린샷에 올리지 마세요.

사용 범위는 [NOTICE.md](../NOTICE.md)를 참고하세요.

<p align="center">
  <img src="../assets/donate-wechat.png" width="240" alt="WeChat 후원 QR" />
  &nbsp;&nbsp;
  <img src="../assets/donate-alipay.jpg" width="240" alt="Alipay 후원 QR" />
</p>
