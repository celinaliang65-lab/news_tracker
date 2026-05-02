import requests
import glob
import os
import pandas as pd
import shioaji as sj
import time
import email.utils
from datetime import datetime, timedelta, timezone
from linebot import LineBotApi
from linebot.models import TextSendMessage
import xml.etree.ElementTree as ET

LINE_ACCESS_TOKEN = os.environ.get(‘LINE_ACCESS_TOKEN’, ‘’).strip()
LINE_USER_ID = “Uf985a37fdacc691e3524e68d2cf68511”
SINOPAC_API_KEY = os.environ.get(‘SINOPAC_API_KEY’, ‘’).strip()
SINOPAC_SECRET_KEY = os.environ.get(‘SINOPAC_SECRET_KEY’, ‘’).strip()
FINMIND_TOKEN = os.environ.get(‘FINMIND_TOKEN’, ‘’).strip()  # 免費版可留空

EXCLUDE_WORDS = [“爆料”, “同學會”, “達人”, “無腦”, “學堂”, “康和”, “券商分點”, “存股”]
THIN_LINE = “─────────────”

# ── 日期工具 ──────────────────────────────────────

def get_last_trading_day():
now_tw = datetime.now(timezone(timedelta(hours=8)))
weekday = now_tw.weekday()
if weekday == 5:
now_tw -= timedelta(days=1)
elif weekday == 6:
now_tw -= timedelta(days=2)
return now_tw

# ── 股價取得 ──────────────────────────────────────

def get_price_twse(sid):
try:
last_day = get_last_trading_day()
date_str = last_day.strftime(”%Y%m%d”)
url = “https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date=” + date_str + “&stockNo=” + sid
headers = {“User-Agent”: “Mozilla/5.0”}
r = requests.get(url, headers=headers, timeout=10)
data = r.json()
rows = data.get(“data”, [])
if not rows:
return None, None
last = rows[-1]
p = float(str(last[6]).replace(”,”, “”))
chg = float(str(last[6]).replace(”,”, “”)) - float(str(last[5]).replace(”,”, “”))
return p, chg
except Exception as e:
print(“TWSE failed “ + sid + “: “ + str(e))
return None, None

def get_price_tpex(sid):
try:
last_day = get_last_trading_day()
roc_year = last_day.year - 1911
ym = str(roc_year) + “/” + last_day.strftime(”%m”)
url = “https://www.tpex.org.tw/web/stock/aftertrading/daily_trading_info/st43_result.php?l=zh-tw&d=” + ym + “&s=” + sid + “&o=json”
headers = {“User-Agent”: “Mozilla/5.0”}
r = requests.get(url, headers=headers, timeout=10)
data = r.json()
rows = data.get(“aaData”, [])
if not rows:
return None, None
last = rows[-1]
p = float(str(last[6]).replace(”,”, “”))
prev = float(str(last[5]).replace(”,”, “”)) if last[5] != “–” else p
chg = round(p - prev, 2)
return p, chg
except Exception as e:
print(“TPEX failed “ + sid + “: “ + str(e))
return None, None

def get_price_shioaji(api, sid):
try:
try:
c = api.Contracts.Stocks[sid]
except:
c = api.Contracts.Stocks.OTC[sid]
if c is None:
return None, None
snap = api.snapshots([c])[0]
p = float(snap.close) if snap.close else None
try:
chg = float(snap.change_price)
except:
chg = None
return p, chg
except Exception as e:
print(“shioaji failed “ + sid + “: “ + str(e))
return None, None

def get_price(api, sid, exchange):
if api:
p, chg = get_price_shioaji(api, sid)
if p and p > 0:
return p, chg
if exchange == “OTC”:
p, chg = get_price_tpex(sid)
else:
p, chg = get_price_twse(sid)
return p, chg

# ── 月營收（改用 FinMind，不怕 GitHub Actions IP 被擋）──

def get_monthly_revenue(sid):
“””
用 FinMind TaiwanStockMonthRevenue dataset。
免費版無需 token，每日有足夠額度。
回傳 (month_str, revenue_億, yoy_%)
“””
try:
now_tw = datetime.now(timezone(timedelta(hours=8)))
# 往前抓 3 個月，確保有資料
start_date = (now_tw - timedelta(days=90)).strftime(”%Y-%m-%d”)
params = {
“dataset”: “TaiwanStockMonthRevenue”,
“data_id”: sid,
“start_date”: start_date,
}
if FINMIND_TOKEN:
params[“token”] = FINMIND_TOKEN

```
    r = requests.get(
        "https://api.finmindtrade.com/api/v4/data",
        params=params,
        timeout=15,
    )
    data = r.json().get("data", [])
    if not data:
        return None, None, None

    last = data[-1]
    revenue = last["revenue"] / 1e8          # 元 → 億
    yoy = last.get("revenue_year_on_year", 0) or 0
    month_str = last["date"][:7]             # "2026-04"
    return month_str, revenue, yoy

except Exception as e:
    print("revenue failed " + sid + ": " + str(e))
    return None, None, None
```

# ── EPS（改用 FinMind TaiwanStockFinancialStatements）──

def get_eps(sid):
“””
用 FinMind 抓最近一季 EPS。
回傳 (quarter_str, eps_float)，例如 (“Q1”, 8.07)
“””
try:
now_tw = datetime.now(timezone(timedelta(hours=8)))
start_date = (now_tw - timedelta(days=180)).strftime(”%Y-%m-%d”)
params = {
“dataset”: “TaiwanStockFinancialStatements”,
“data_id”: sid,
“start_date”: start_date,
}
if FINMIND_TOKEN:
params[“token”] = FINMIND_TOKEN

```
    r = requests.get(
        "https://api.finmindtrade.com/api/v4/data",
        params=params,
        timeout=15,
    )
    rows = r.json().get("data", [])
    if not rows:
        return None, None

    # 篩出 EPS 那筆 (type == "EPS")
    eps_rows = [row for row in rows if row.get("type") == "EPS"]
    if not eps_rows:
        return None, None

    last = eps_rows[-1]
    date_str = last["date"]  # "2026-03-31"
    month = int(date_str[5:7])
    # 季度對應
    quarter_map = {3: "Q1", 6: "Q2", 9: "Q3", 12: "Q4"}
    quarter = quarter_map.get(month, "Q?")
    eps = float(last["value"])
    return quarter, eps

except Exception as e:
    print("EPS failed " + sid + ": " + str(e))
    return None, None
```

# ── 新聞 ──────────────────────────────────────────

def get_news(stock_name, stock_id, max_news=2):
try:
query = stock_name + “ “ + stock_id
url = “https://news.google.com/rss/search?q=” + query + “&hl=zh-TW&gl=TW&ceid=TW:zh-Hant”
headers = {“User-Agent”: “Mozilla/5.0”}
r = requests.get(url, headers=headers, timeout=10)
root = ET.fromstring(r.content)
items = root.findall(”.//item”)
news_list = []
now_tw = datetime.now(timezone(timedelta(hours=8)))

```
    for item in items:
        if len(news_list) >= max_news:
            break
        try:
            pub_date_str = item.find("pubDate").text
            pub_date = email.utils.parsedate_to_datetime(pub_date_str)
            age_hours = (now_tw - pub_date.astimezone(timezone(timedelta(hours=8)))).total_seconds() / 3600
            if age_hours > 48:
                continue
        except:
            continue
        title = item.find("title").text
        if not title:
            continue
        if " - " in title:
            title = title.rsplit(" - ", 1)[0]
        title = title.strip()
        if any(word in title for word in EXCLUDE_WORDS):
            continue
        if len(title) > 25:
            title = title[:25] + "..."
        news_list.append(title)
    return news_list
except Exception as e:
    print("news failed " + stock_id + ": " + str(e))
    return []
```

# ── 主程式 ────────────────────────────────────────

def job():
excel_files = glob.glob(”*.xlsx”)
if not excel_files:
print(“no excel found”)
return

```
target_file = next((f for f in excel_files if "觀察清單" in f), None)
if not target_file:
    print("找不到觀察清單檔案")
    return
print("reading: " + target_file)

df_watch = pd.read_excel(target_file, sheet_name="觀察清單", dtype={"代號": str})
df_watch = df_watch.dropna(subset=["代號", "名稱"])

now_tw = datetime.now(timezone(timedelta(hours=8))).strftime("%Y/%m/%d %H:%M")

api = sj.Shioaji()
try:
    api.login(api_key=SINOPAC_API_KEY, secret_key=SINOPAC_SECRET_KEY)
    time.sleep(3)
    print("shioaji logged in")
except Exception as e:
    print("shioaji login failed: " + str(e))
    api = None

report = "📰 觀察清單新聞摘要\n      " + now_tw + "\n"
report += "━━━━━━━━━━━━━\n"
report += "【觀察清單】\n"

for _, row in df_watch.iterrows():
    sid = str(row["代號"]).strip()
    name = str(row["名稱"]).strip()
    exchange = str(row.get("交易所", "TSE")).strip()
    print("fetching watch: " + sid + " (" + exchange + ")")

    p, chg = get_price(api, sid, exchange)

    report += "\n" + sid + " " + name + "\n"

    if p is not None and p > 0:
        if chg is not None and chg > 0:
            day_str = "🔺 +" + "{:.2f}".format(chg)
        elif chg is not None and chg < 0:
            day_str = "🔽 " + "{:.2f}".format(chg)
        else:
            day_str = "➖ 0.00"
        report += "  現價:" + "{:.2f}".format(p) + "  " + day_str + "\n"
    else:
        report += "  價格取得失敗\n"

    # 月營收
    month_str, revenue, yoy = get_monthly_revenue(sid)
    if month_str and revenue:
        yoy_sign = "+" if yoy >= 0 else ""
        yoy_arrow = "↑" if yoy >= 0 else "↓"
        report += "  月營收：" + month_str + " " + "{:.1f}".format(revenue) + "億  " + yoy_arrow + " " + yoy_sign + "{:.1f}".format(yoy) + "%\n"

    # EPS
    quarter, eps = get_eps(sid)
    if quarter and eps:
        report += "  EPS：" + quarter + " " + "{:.2f}".format(eps) + "元\n"

    # 新聞
    news_list = get_news(name, sid)
    report += THIN_LINE + "\n"
    if news_list:
        for news in news_list:
            report += "  ・" + news + "\n"
    else:
        report += "  暫無最新新聞\n"

report += "\n━━━━━━━━━━━━━"

try:
    LineBotApi(LINE_ACCESS_TOKEN).push_message(
        LINE_USER_ID,
        TextSendMessage(text=report)
    )
    print("news sent!")
except Exception as e:
    print("LINE failed: " + str(e))
finally:
    if api:
        try:
            api.logout()
        except:
            pass
```

if **name** == “**main**”:
job()
