<div align="center">

<sub><strong>L0NE-6 · DAILY SIGNAL</strong></sub>

# 🟦 WPS Lingxi Daily

**WPS 灵犀每日签到 · 双域回退 · 多账号单文件 Python**

> 当前版本：**v1.0.0**（2026-11-24）

[简体中文](README.md) · [English](docs/README.en.md) · [繁體中文](docs/README.zh-Hant.md) · [日本語](docs/README.ja.md) · [한국어](docs/README.ko.md) · [Português (BR)](docs/README.pt-BR.md)

🔐 Cookie 隔离 · 🌐 wps.cn / kdocs.cn · 🎯 `daily_check_in` · ✅ 任务与余额双回读 · 🧾 JSONL · 👥 多账号 · 📢 推送 · ☁️ Actions

<img src="https://img.shields.io/badge/version-v1.0.0-2ea44f?style=for-the-badge" />
<img src="https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
<img src="https://img.shields.io/badge/Deploy-Actions%20%7C%20Qinglong-2088FF?style=for-the-badge&logo=githubactions&logoColor=white" />
<img src="https://img.shields.io/badge/License-MIT-F472B6?style=for-the-badge" />

[✨ 速览](#-30-秒速览) · [🔐 账号格式](#-账号格式) · [🔧 环境变量](#-环境变量) · [☁️ Actions](#-github-actions) · [✅ 回读判据](#-严格回读) · [🧪 测试](#-离线测试) · [🚫 使用边界](#-使用边界) · [✦ 星轨](#-星轨-star-trail)

</div>

---

## ✨ 30 秒速览

| 维度 | 说明 |
| :--- | :--- |
| **做什么** | 执行 WPS 灵犀每日签到，领取 `daily_check_in` 奖励并核对余额。 |
| **输入** | `WPSLINGXI_COOKIES`，每行 `备注|wps_sid|uid` 或完整 Cookie。 |
| **流程** | 任务列表找 `daily_check_in` → 选择日期 → claim → 回读任务 → 回读余额。 |
| **成功判据** | claim 后任务状态必须为 `claimed`，并成功读取签到后余额。 |
| **输出** | 中文汇总 + 可选推送 + 每账号一行 JSONL。 |
| **依赖** | Python 3.8+，仅 `requests`。 |

---

## 🔐 账号格式

推荐：

```text
主号|wps_sid_xxx|123456
备号|wps_sid_yyy|789012
```

也支持完整 Cookie：

```text
主号|wps_sid=xxx; uid=123456
```

规则：

1. 每行一个账号，也支持用 `&` 分隔。
2. 三段格式是 `备注|wps_sid|uid`。
3. 完整 Cookie 必须包含 `wps_sid=`。
4. 不要把 Cookie、`wps_sid`、uid 写进脚本、README、Issue 或公开日志。

---

## 🔧 环境变量

| 变量 | 必填 | 说明 |
| :--- | :---: | :--- |
| `WPSLINGXI_COOKIES` | ⬜ | 多账号 Cookie。 |
| `WPSLINGXI_COOKIE` | ⬜ | 单账号兼容变量。 |
| `WPSLINGXI_JSONL` | ⬜ | JSONL 路径，默认 `wpslingxi_results.jsonl`。 |
| `WPSLINGXI_NOTIFY` | ⬜ | `always`（默认）/ `fail` / `0`。 |
| `PUSHPLUS_TOKEN` | ⬜ | PushPlus Token。 |
| `BARK_URL` | ⬜ | Bark 完整地址。 |
| `SERVERCHAN_SENDKEY` | ⬜ | Server酱 SendKey。 |
| `WXPUSHER_APP_TOKEN` | ⬜ | WxPusher App Token。 |
| `WXPUSHER_UID` | ⬜ | WxPusher UID。 |
| `WECOM_WEBHOOK` | ⬜ | 企业微信群机器人 Webhook。 |
| `DINGTALK_WEBHOOK` | ⬜ | 钉钉机器人 Webhook。 |
| `DINGTALK_SECRET` | ⬜ | 钉钉加签密钥。 |

---

## 🐧 青龙面板

```bash
pip3 install -r requirements.txt
python3 wpslingxi_daily.py
```

青龙任务命令：

```bash
task wpslingxi_daily.py
```

建议北京时间：`07:31`。

---

## ☁️ GitHub Actions

仓库内置：

- `.github/workflows/wpslingxi.yml`：每日北京时间约 07:31 执行。
- `.github/workflows/test.yml`：push / PR 自动测试。

在 `Settings → Secrets and variables → Actions` 添加 `WPSLINGXI_COOKIES` 或 `WPSLINGXI_COOKIE`。

---

## ✅ 严格回读

```text
GET  /api/public/v1/tasks
GET  /api/public/v1/credits/balance
POST /api/public/v1/tasks/daily_check_in/claim?date=...
GET  /api/public/v1/tasks
GET  /api/public/v1/credits/balance
```

脚本优先访问 `lingxi.wps.cn`；遇到 401/403 或 `UserUnauthorized` 时回退到 `lingxi.kdocs.cn`。

结果：

| 结果 | 含义 |
| :--- | :--- |
| `done` | 签到前已领取，或回读已领取但余额未变化。 |
| `claimed` | 回读任务已领取且余额出现正增长。 |
| `failed` | 网络、协议、任务回读或余额读取失败。 |

HTTP 200、claim 请求本身或单个 `result=ok` 都不算完成。

---

## 🧾 JSONL

每个账号追加一行，例如：

```json
{"provider":"wps-lingxi","label":"主号","outcome":"claimed","ok":true,"credit":10,"message":"服务端确认签到，余额 +10"}
```

JSONL 不写入 Cookie、`wps_sid` 或 uid。

---

## 🧪 离线测试

```bash
python -m unittest discover -s tests -v
python -m compileall -q wpslingxi_daily.py tests
```

覆盖已签到短路、完整签到、date 选择、双域回退、任务回读、余额变化和 JSONL 脱敏。

---

## 🚫 使用边界

> **官方版本永久免费。** 未经作者书面许可，禁止付费包装、搬运引流、冒充作者，或使用作者身份与二维码制造官方授权假象。完整规则见 [NOTICE.md](NOTICE.md)。

---

## ☕ 支持与投喂

<p align="center">
  <img src="assets/donate-wechat.png" width="260" alt="微信赞赏码" />
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
  <img src="assets/donate-alipay.jpg" width="260" alt="支付宝收款码" />
</p>
<p align="center"><sub>💚 微信支付（左） &nbsp;|&nbsp; 💙 支付宝（右）</sub></p>

收款码仅用于向作者自愿赞赏。

---

## ✦ 星轨 Star Trail

<a href="https://star-history.com/#L0NE-6/WPSLingxi-Daily&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=L0NE-6/WPSLingxi-Daily&type=Date&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=L0NE-6/WPSLingxi-Daily&type=Date" />
    <img alt="WPS Lingxi Daily Star Trail" src="https://api.star-history.com/svg?repos=L0NE-6/WPSLingxi-Daily&type=Date" />
  </picture>
</a>

<div align="center"><sub>L0NE-6 · DAILY SIGNAL · 点个 Star，让下一轮自动化有迹可循 ✨</sub></div>
