<div align="center">

<sub><strong>L0NE-6 · WPS LINGXI SIGNAL</strong></sub>

# WPS Lingxi Daily

**WPS 灵犀每日签到 · 双域回退 · 任务与余额双回读**

> 当前版本：**v1.0.0**（2026-11-24） · daily_check_in 任务按日期领取，主域失败仅做有界回退

[简体中文](README.md) · [English](docs/README.en.md) · [繁體中文](docs/README.zh-Hant.md) · [日本語](docs/README.ja.md) · [한국어](docs/README.ko.md) · [Português (BR)](docs/README.pt-BR.md)

<img src="https://img.shields.io/badge/Features-Dual-domain-6F42C1?style=for-the-badge" alt="Features" />
<a href="https://github.com/L0NE-6/WPSLingxi-Daily/releases"><img src="https://img.shields.io/github/v/release/L0NE-6/WPSLingxi-Daily?style=for-the-badge&label=Release&color=2ea44f&logo=github" alt="Release" /></a>
<a href="https://github.com/L0NE-6/WPSLingxi-Daily/stargazers"><img src="https://img.shields.io/github/stars/L0NE-6/WPSLingxi-Daily?style=for-the-badge&label=Stars&color=FFC75F&logo=github" alt="Stars" /></a>
<img src="https://img.shields.io/badge/Python-3.8%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
<img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20Qinglong-4EAA25?style=for-the-badge&logo=linux&logoColor=white" alt="Platform" />
<img src="https://img.shields.io/badge/License-MIT-F472B6?style=for-the-badge" alt="License" />

🔐 Cookie 隔离 · 🌐 wps.cn / kdocs.cn · 🎯 daily_check_in · ✅ 任务与余额回读 · 🧾 JSONL · ☁️ Actions

[⚡ 30 秒速览](#quick-look) · [🔁 协议与回读](#protocol) · [🔐 凭据](#credentials) · [🐧 青龙](#qinglong) · [☁️ Actions](#actions) · [⌨️ CLI](#cli-json) · [✅ 成功判据](#success) · [✦ 星轨](#star-trail)

</div>

---

<a id="usage-policy"></a>
## 🚫 使用边界与禁止倒卖

> [!IMPORTANT]
> **官方版本永久免费。** 未经作者书面许可，禁止倒卖、付费包装、搬运引流、冒充作者，或使用作者身份与二维码制造官方授权假象。

本仓库、脚本、部署说明和 Release 下载保持免费公开。禁止将本项目或其轻度改名版本包装为付费资源、内部版、独家版、会员权益、收费课程、代部署服务或包更新服务；禁止搬运到其他账号、群组、频道、网盘、电商平台或付费社群进行涨粉、截流、倒卖和引流；禁止删除作者与版权信息后冒充原创。

完整规则见 [NOTICE.md](NOTICE.md)。第三方以“下载费 / 激活费 / 内部版 / 代部署 / 会员门槛”等名义收费，均与作者无关，请停止付款并保留证据。

---

<a id="quick-look"></a>
## ⚡ 30 秒速览

| 维度 | 说明 |
| :--- | :--- |
| **做什么** | 执行 WPS 灵犀每日签到，领取 `daily_check_in` 奖励并核对余额。 |
| **输入** | `WPSLINGXI_COOKIES`，每行 `备注\|wps_sid\|uid` 或完整 Cookie。 |
| **流程** | 任务列表找 `daily_check_in` → 选择日期 → claim → 回读任务 → 回读余额。 |
| **成功判据** | claim 后任务状态为 `claimed`，并成功读取签到后余额。 |
| **输出** | 中文汇总 + 可选推送 + 每账号一行 JSONL。 |
| **依赖** | Python 3.8+，仅 `requests`。 |

---

## 🧭 这是什么 / 覆盖范围

WPS 灵犀脚本从任务中心读取 `daily_check_in`，根据 `extra.check_in_days` 选择可领取日期，提交 claim 后重新读取任务和余额。

### 覆盖范围

- `备注|wps_sid|uid` 与完整 Cookie 两种账号形式。
- 主域 `lingxi.wps.cn`，遇到 401/403、`UserUnauthorized` 或主域不存在时回退 `lingxi.kdocs.cn`。
- `task_key=daily_check_in` 任务发现。
- `status=claimed` 回读和 `total_balance` / `balance` 余额回读。
- JSONL、中文摘要和可选多渠道通知。

---

<a id="protocol"></a>
## 🔁 协议与回读流程

### 请求链

```http
GET  /api/public/v1/tasks
GET  /api/public/v1/credits/balance
POST /api/public/v1/tasks/daily_check_in/claim?date=YYYY-MM-DD
GET  /api/public/v1/tasks
GET  /api/public/v1/credits/balance
```

### 关键字段

| 字段 | 说明 |
| :--- | :--- |
| `data.tasks[]` | 任务列表。 |
| `task_key=daily_check_in` | 每日签到任务。 |
| `extra.check_in_days` | 可选日期与 `available` 状态。 |
| `status` | 任务状态，成功值为 `claimed` / `completed` / `complete` / `done`。 |
| `total_balance` / `balance` | 余额字段。 |
| `result` | claim 响应结果；`ok` 之外按业务错误处理。 |

主域返回鉴权失败或不存在时切换到 `lingxi.kdocs.cn`。claim 后任务未变为已领取，或余额读取失败，都按失败处理。

---

<a id="credentials"></a>
## 🔐 凭据与环境变量

### 账号格式

```text
主号|wps_sid_xxx|123456
备号|wps_sid=xxx; uid=123456
```

| 变量 | 必填 | 说明 |
| :--- | :---: | :--- |
| `WPSLINGXI_COOKIES` | 二选一 | 多账号 Cookie。 |
| `WPSLINGXI_COOKIE` | 二选一 | 单账号 Cookie。 |
| `WPSLINGXI_JSONL` | 否 | JSONL 路径，默认 `wpslingxi_results.jsonl`。 |
| `WPSLINGXI_NOTIFY` | 否 | `always` / `fail` / `0`。 |
| `PUSHPLUS_TOKEN` / `BARK_URL` | 否 | 推送。 |
| `SERVERCHAN_SENDKEY` | 否 | Server酱。 |
| `WXPUSHER_APP_TOKEN` / `WXPUSHER_UID` | 否 | WxPusher。 |
| `WECOM_WEBHOOK` | 否 | 企业微信机器人。 |
| `DINGTALK_WEBHOOK` / `DINGTALK_SECRET` | 否 | 钉钉机器人。 |

---

## 💻 本地快速开始

### PowerShell

```powershell
python -m pip install -r requirements.txt
$env:WPSLINGXI_COOKIE = "wps_sid=xxx; uid=123456"
python wpslingxi_daily.py
```

### Bash

```bash
python -m pip install -r requirements.txt
export WPSLINGXI_COOKIE='wps_sid=xxx; uid=123456'
python wpslingxi_daily.py
```

常用参数：`--only 2`、`--no-notify`、`--jsonl wpslingxi_results.jsonl`、`--version`。

---

<a id="qinglong"></a>
## 🐧 青龙

1. 在青龙依赖管理中安装 `requests`，或执行 `pip3 install -r requirements.txt`。
2. 上传 `wpslingxi_daily.py` 到脚本目录。
3. 在环境变量中配置 `WPSLINGXI_COOKIES` 或 `WPSLINGXI_COOKIE`。
4. 新建定时任务，命令使用 `task wpslingxi_daily.py`，不要直接写裸 `python`。
5. 建议北京时间：`31 7 * * *`。青龙按面板本地时间执行。

```bash
pip3 install -r requirements.txt
task wpslingxi_daily.py
```

---

<a id="actions"></a>
## ☁️ GitHub Actions、Secrets 与定时

工作流：`.github/workflows/wpslingxi.yml`；测试工作流：`.github/workflows/test.yml`。

| 事件 | 行为 |
| :--- | :--- |
| `schedule` | 每天执行离线测试和签到。 |
| `workflow_dispatch` | 手动执行。 |
| 未配置账号 | 输出 warning 并跳过在线签到。 |

### Secrets

| Secret | 说明 |
| :--- | :--- |
| `WPSLINGXI_COOKIES` | 多账号 Cookie。 |
| `WPSLINGXI_COOKIE` | 单账号 Cookie。 |
| `WPSLINGXI_JSONL` / `WPSLINGXI_NOTIFY` | 输出路径与推送策略。 |
| `PUSHPLUS_TOKEN` / `BARK_URL` / `SERVERCHAN_SENDKEY` | 推送。 |
| `WXPUSHER_APP_TOKEN` / `WXPUSHER_UID` | WxPusher。 |
| `WECOM_WEBHOOK` | 企业微信机器人。 |
| `DINGTALK_WEBHOOK` / `DINGTALK_SECRET` | 钉钉机器人。 |

内置定时为 UTC `31 23 * * *`，对应北京时间约 07:31。工作流不单独上传 artifact，JSONL 按 `WPSLINGXI_JSONL` 写入。

---

<a id="cli-json"></a>
## ⌨️ CLI 与 JSON 输出

```powershell
python wpslingxi_daily.py
python wpslingxi_daily.py --only 2
python wpslingxi_daily.py --no-notify
python wpslingxi_daily.py --jsonl wpslingxi_results.jsonl
```

JSONL 每账号一行：

```json
{"ts":"2026-11-24T00:00:00+00:00","provider":"wps-lingxi","label":"主号","outcome":"claimed","ok":true,"credit":10,"message":"服务端确认签到，余额 +10","detail":{"base":"https://lingxi.wps.cn","date":"2026-11-24","task_after":{"status":"claimed"}}}
```

| 字段 | 说明 |
| :--- | :--- |
| `provider` / `label` | 服务名与脱敏备注。 |
| `outcome` / `ok` | 结果码与是否成功。 |
| `credit` | 余额正增长值。 |
| `detail` | 域名、日期、任务和余额前后状态。 |

---

<a id="result-codes"></a>
## 🧾 结果码

| 结果码 | 成功 | 含义 |
| :--- | :---: | :--- |
| `done` | 是 | 签到前已领取，或回读已领取但余额未变化。 |
| `claimed` | 是 | 回读任务已领取且余额正增长。 |
| `failed` | 否 | 网络、鉴权、协议、任务回读或余额读取失败。 |

底层错误类别包括 `NetworkError`、`ProtocolError`、`AuthError` 和 `ApiError`。进程退出码为 0 表示全部账号成功，否则为 1。

---

<a id="success"></a>
## ✅ 成功判据

| 场景 | 必须满足 |
| :--- | :--- |
| 今日已签到 | `daily_check_in` 在运行前已是已领取状态。 |
| 本次签到 | claim 后任务状态为 `claimed` 等完成状态。 |
| 奖励确认 | 签到后余额可读；余额正增长记 `claimed`，余额不变记 `done`。 |
| 回退 | 仅主域鉴权失败或不存在时使用备用域。 |

---

## 🧪 测试与静态检查

```bash
python -m unittest discover -s tests -v
python -m compileall -q wpslingxi_daily.py tests
python -m ruff check .
```

离线测试覆盖 Cookie/UID 解析、完整签到、日期选择、双域回退、任务回读、余额变化和 JSONL 不含 Cookie。

---

## 🧱 设计原则

- **任务发现优先**：按 `task_key` 找每日任务。
- **日期来自服务端**：优先选择当天或 `available` 日期。
- **双域有界**：只在鉴权失败或主域不存在时回退。
- **任务与余额双读**：claim 回执不是最终成功。
- **Cookie 脱敏**：JSONL 不含 `wps_sid` 或 uid。

---

## 🔒 隐私

仓库不包含 Cookie、`wps_sid`、UID、账号、手机号、日志或真实响应。`wpslingxi_results.jsonl`、`.env`、日志和缓存已由 `.gitignore` 排除。

---

## 📁 目录结构

```text
WPSLingxi-Daily/
├── .github/workflows/wpslingxi.yml
├── .github/workflows/test.yml
├── assets/
│   ├── donate-alipay.jpg
│   └── donate-wechat.png
├── docs/
│   ├── README.en.md
│   ├── README.zh-Hant.md
│   ├── README.ja.md
│   ├── README.ko.md
│   └── README.pt-BR.md
├── tests/test_wpslingxi_daily.py
├── CHANGELOG.md
├── LICENSE
├── NOTICE.md
├── THIRD_PARTY_NOTICES.md
├── wpslingxi_daily.py
├── pyproject.toml
├── README.md
└── requirements.txt
```

---

## 📦 版本与发布

- 当前清单版本：`v1.0.0`，日期 `2026-11-24`。
- 脚本版本与 `wpslingxi_daily.py` 内的 `VERSION` 保持一致。
- 更新记录见 [CHANGELOG.md](CHANGELOG.md)，下载入口见 [Releases](https://github.com/L0NE-6/WPSLingxi-Daily/releases)。
- Release 徽标由 GitHub 实时生成；如果页面尚未创建对应 Release，以 `CHANGELOG.md` 和仓库提交为准。

---

## ⚠️ 免责声明

本项目用于个人学习与个人自动化。WPS 灵犀 的活动规则、接口、奖励、风控策略和账号资格由服务方决定。使用前请确认对应服务条款，并自行承担接口变化、账号限制和网络环境带来的风险。

---

## ☕ 支持与投喂

脚本完全免费，赞赏纯自愿，不影响任何功能，也不影响 Issue 响应。

<p align="center">
  <img src="assets/donate-wechat.png" width="260" alt="微信赞赏码" />
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
  <img src="assets/donate-alipay.jpg" width="260" alt="支付宝收款码" />
</p>
<p align="center"><sub>💚 微信支付（左） &nbsp;|&nbsp; 💙 支付宝（右，支持信用卡 / 花呗）</sub></p>

> 收款码仅用于向作者自愿赞赏。任何第三方以代下载、代部署、内部资源或会员群为由收费，均与作者无关。

---

## 💬 反馈与贡献

- 提交 [Issue](https://github.com/L0NE-6/WPSLingxi-Daily/issues) 时附运行日志、脱敏后的错误字段和复现步骤。
- 发起 [Pull Request](https://github.com/L0NE-6/WPSLingxi-Daily/pulls) 时保持单文件运行、离线测试和凭据脱敏约束。
- 不要在任何 Issue、PR、截图或日志中粘贴真实 Token、Cookie、密码、UID、手机号或邮箱。

---

<a id="star-trail"></a>
## ✦ Star History / 星轨

<a href="https://star-history.com/#L0NE-6/WPSLingxi-Daily&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=L0NE-6/WPSLingxi-Daily&type=Date&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=L0NE-6/WPSLingxi-Daily&type=Date" />
    <img alt="WPSLingxi-Daily Star History" src="https://api.star-history.com/svg?repos=L0NE-6/WPSLingxi-Daily&type=Date" />
  </picture>
</a>

<div align="center">
  <sub>L0NE-6 · DAILY SIGNAL &nbsp;|&nbsp; 点个 <b>Star</b>，让下一轮自动化有迹可循</sub>
</div>
