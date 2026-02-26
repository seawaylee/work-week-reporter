# Week Reporter

这是一个用于自动化生成搜狐 Odin 服务周报的 Python 脚本。

## 功能

1.  **数据抓取**：
    *   从天象台 (Tianxiangtai) API 获取各服务的 Requests, P99, P999 等核心指标。
    *   从 Grafana API 获取各服务的峰值 QPS 数据。
2.  **Excel 处理**：
    *   基于上一周的周报 Excel 文件（模板）。
    *   自动识别服务区块位置。
    *   执行“滚动更新”：保留最近 4 周的数据，删除最旧的一周，写入最新一周的数据。
    *   **样式保持**：自动复制上一行的字体、边框、对齐方式，确保报表美观。
    *   **数据清洗**：自动将指标取整，并将 API 的总请求数转换为 Excel 要求的“日均请求数”。

## 环境依赖

需要 Python 3.x 及以下库：

```bash
pip install pandas openpyxl requests
```

## 快速开始

1.  确保目录中存在上一周的周报文件（例如 `周报2026-01-09.xlsx`）。
2.  设置环境变量（不再在代码里硬编码 Cookie/Token）：

```bash
export TXT_URL='https://txt.mptc.sohu-inc.com/data/api/board/aggregateData/get?...'
export TXT_COOKIE='你的天象台 Cookie'
export GRAFANA_COOKIE='grafana_session=...'
# 可选
export GRAFANA_URL='https://grafana-m0ymy2z9.grafana.tencent-cloud.com/api/datasources/proxy/1/api/v1/query_range'
export GRAFANA_ORG_ID='1'
```

3.  如需修改模板文件，可改 `generate_weekly_report.py` 的 `INPUT_FILE`。
4.  运行脚本：

```bash
python3 generate_weekly_report.py
```

5.  脚本将在当前目录下生成当天的周报，例如 `周报2026-02-10.xlsx`。

## 定时任务（每周五 09:30）

项目已提供定时任务脚本与安装脚本：

* `scripts/weekly_report_job.sh`
* `scripts/install_weekly_cron.sh`

安装 cron（当前用户）：

```bash
./scripts/install_weekly_cron.sh
```

安装后会写入：

```cron
30 9 * * 5 /Users/NikoBelic/app/git/week-reporter/scripts/weekly_report_job.sh >> /Users/NikoBelic/app/git/week-reporter/logs/weekly_report_cron.log 2>&1
```

## OpenClaw 通知（sohu）

`scripts/weekly_report_job.sh` 的行为：

1. 执行 `generate_weekly_report.py`。
2. 自动查找本次生成的 `周报*.xlsx`。
3. 将 Excel 复制到 `~/.openclaw/workspace-sohu/inbox/week-reporter/`。
4. 调用 OpenClaw 本地 agent：`sohu`。
5. **无论执行成功还是失败，都会发送通知**（通知里包含状态、日志路径、Excel 路径）。

手动测试一次（不跑真实报表，仅测试通知链路）：

```bash
DRY_RUN=1 ./scripts/weekly_report_job.sh
```

## 维护说明

*   **Cookie 过期**：如果运行报错 401/403，请在浏览器中登录天象台/Grafana，按 F12 抓取最新 Cookie，并更新对应环境变量（`TXT_COOKIE`、`GRAFANA_COOKIE`）。
*   **新增服务**：如果需要监控新的服务，请在 `SERVICE_MAPPING` 和 `GRAFANA_MAPPING` 字典中添加相应的映射关系。
*   **OpenClaw 不可用**：先检查 `openclaw agent --local --agent sohu --message "ping"` 是否可执行，再检查模型/API 配置。
