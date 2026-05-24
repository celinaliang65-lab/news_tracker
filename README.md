# news_tracker.py
## 台股觀察清單新聞摘要推播系統（姊姊版）
### 說明文件 v1.3 ｜ 2026-05-24

---

## 一、系統概述

`news_tracker.py` 是一套自動化台股資訊推播腳本，定期從多個資料來源抓取觀察清單中各股票的：

- 即時或最新收盤股價與漲跌幅
- 月營收（含月增率 MoM）
- 最新季度 EPS
- 近 48 小時內的 Google News 新聞標題

整合後排版成結構化文字報告，透過 LINE Messaging API 推播至指定使用者。

---

## 二、環境需求與設定

### 2.1 Python 套件

| 套件 | 用途 |
|------|------|
| requests | HTTP 請求（TWSE / TPEX / FinMind / Google News）|
| pandas | 讀取 Google Sheets 觀察清單 |
| shioaji | 永豐金 API 即時股價（選用）|
| linebot | LINE 訊息推播 |
| xml.etree.ElementTree | 解析 Google News RSS |
| google-auth | Google Service Account 認證 |
| google-api-python-client | Google Sheets API 讀取 |

### 2.2 環境變數

| 變數名稱 | 說明 | 必填 |
|----------|------|------|
| LINE_ACCESS_TOKEN | LINE Channel Access Token | ✅ |
| LINE_USER_ID | LINE 推播目標用戶 ID | ✅ |
| SINOPAC_API_KEY | 永豐金 Shioaji API Key | 選用 |
| SINOPAC_SECRET_KEY | 永豐金 Shioaji Secret Key | 選用 |
| FINMIND_TOKEN | FinMind API Token（提升速率限制）| 選用 |
| GOOGLE_CREDENTIALS | Google Service Account JSON 金鑰（全文）| ✅ |
| SPREADSHEET_ID | Google Sheets 試算表 ID | ✅ |

### 2.3 Google Sheets 設定

程式從 Google Sheets 讀取觀察清單，不再使用本地 Excel 檔案。

| 項目 | 說明 |
|------|------|
| Spreadsheet ID | 從 GitHub Secrets `SPREADSHEET_ID` 讀取 |
| 姊姊的 Sheet ID | `1LR7yZlngjwlH-RMh3xLhi-vVQdi5rDdLdxMy4lvtwLk` |
| Sheet tab 名稱 | `觀察清單` |
| 必要欄位 | 代號、名稱、交易所 |

**Google Sheets 設定步驟：**
1. 確認 Google Sheet 已分享給 Service Account：`stock-tracker-bot@stock-tracker-496215.iam.gserviceaccount.com`，權限為**編輯者**
2. GitHub repo Secrets 加入 `GOOGLE_CREDENTIALS`（Service Account JSON 全文）
3. GitHub repo Secrets 加入 `SPREADSHEET_ID`
4. workflow `.yml` 的 env 區塊加入對應的 Secrets

### 2.4 觀察清單 Google Sheets 欄位格式

| 欄位名稱 | 說明 | 範例 |
|----------|------|------|
| 代號 | 股票代號（字串格式）| 2330 |
| 名稱 | 股票中文名稱 | 台積電 |
| 交易所 | TSE（上市）或 OTC（上櫃）| TSE |

### 2.5 requirements.txt

```
shioaji
pandas
openpyxl
line-bot-sdk
requests
google-auth
google-api-python-client
```

### 2.6 workflow news.yml 範例

```yaml
name: Stock News Tracker

on:
  workflow_dispatch:
  schedule:
    - cron: '0 20 * * 1-5'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run news script
        env:
          LINE_ACCESS_TOKEN: ${{ secrets.LINE_ACCESS_TOKEN }}
          LINE_USER_ID: ${{ secrets.LINE_USER_ID }}
          SINOPAC_API_KEY: ${{ secrets.SINOPAC_API_KEY }}
          SINOPAC_SECRET_KEY: ${{ secrets.SINOPAC_SECRET_KEY }}
          GOOGLE_CREDENTIALS: ${{ secrets.GOOGLE_CREDENTIALS }}
          SPREADSHEET_ID: ${{ secrets.SPREADSHEET_ID }}
        run: python news_tracker.py
```

---

## 三、功能說明

### 3.1 股價取得

採三層 fallback 機制，確保資料穩定：

- 第一優先：Shioaji（永豐金即時 API）
- 第二優先（上市）：台灣證券交易所 TWSE API
- 第二優先（上櫃）：證券櫃檯買賣中心 TPEX API

| 情況 | 顯示範例 |
|------|----------|
| 上漲 | 現價：409.00  🔺 +0.50 |
| 下跌 | 現價：219.50  🔽 -5.50 |
| 平盤 | 現價：100.00  ➖ 0.00 |

### 3.2 月營收

資料來源：FinMind `TaiwanStockMonthRevenue`

> **重要說明：** FinMind 的 `date` 欄位為「公布日期（次月）」，程式會自動將其還原為實際營收月份（公布月 − 1）。

| 項目 | 說明 |
|------|------|
| 比較基準 | MoM 月增率（與前一個月比較）|
| 顯示格式 | `月營收：2026-03  84.7億  ↑ +19.96%MoM` |
| 資料回溯 | 抓取最近 120 天資料以確保有兩筆可計算 MoM |

### 3.3 EPS

資料來源：FinMind `TaiwanStockFinancialStatements`，篩選 `type = EPS` 欄位。

| 項目 | 說明 |
|------|------|
| 季度格式 | `4Q25`（季數在前、末兩碼年份在後）|
| 對應規則 | date 月份 3→Q1、6→Q2、9→Q3、12→Q4 |
| 顯示範例 | `EPS：4Q25  19.51元` |

### 3.4 新聞

資料來源：Google News RSS，查詢條件為「股票名稱 + 代號」。

- 每檔股票最多顯示 2 則新聞
- 僅顯示 48 小時內的新聞
- 標題超過 25 字自動截斷並加「...」
- 過濾含以下關鍵字的新聞：爆料、同學會、達人、無腦、學堂、康和、券商分點、存股

### 3.5 LINE 推播格式

```
📰 觀察清單新聞摘要
      2026/05/24 04:00
━━━━━━━━━━━━━

2330 台積電
  現價：950.00  🔺 +10.00
  月營收：2026-03  2650.0億  ↑ +5.2%MoM
  EPS：4Q25  14.45元
─────────────
  ・台積電 CoWoS 需求持續強勁...
  ・法人上調台積電目標價至 1200...

━━━━━━━━━━━━━
```

---

## 四、常見問題

| 問題 | 原因與解法 |
|------|------------|
| 價格取得失敗 | Shioaji 登入失敗時自動 fallback 至 TWSE/TPEX；若三者均失敗則顯示「價格取得失敗」|
| 月營收無資料 | FinMind 免費版有速率限制，建議設定 FINMIND_TOKEN 環境變數 |
| EPS 無資料 | 財報資料延遲公布屬正常現象，回溯 180 天仍無資料表示尚未申報 |
| 暫無最新新聞 | Google News 48 小時內無相關報導，或標題均被關鍵字過濾 |
| LINE 推播失敗 | 確認 LINE_ACCESS_TOKEN 正確且未過期，LINE_USER_ID 格式正確（U 開頭）|
| gsheet service failed | GOOGLE_CREDENTIALS 未設定或 workflow env 未加入 |
| Google Sheets connection failed | Secret 內容有誤或 Sheet 未分享給 Service Account |

---

## 五、變更紀錄

| 日期 | 版本 | 更新內容 |
|------|------|----------|
| 2026-05-03 | v1.1 | 修正月營收月份錯誤、MoM 改為月增率、EPS 季度格式加年份 |
| 2026-05-16 | v1.2 | 改從 Google Sheets 讀取觀察清單（取代本地 Excel）、加入 GOOGLE_CREDENTIALS 設定說明 |
| 2026-05-24 | v1.3 | LINE_USER_ID 和 SPREADSHEET_ID 改從環境變數讀取、排程改為週一至週五（1-5）、workflow 範例更新 |

---

*文件結束　建立者：Claude (Anthropic)　更新日期：2026/05/24*
