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

LINE_ACCESS_TOKEN = os.environ.get('LINE_ACCESS_TOKEN', '').strip()
SINOPAC_API_KEY = os.environ.get('SINOPAC_API_KEY', '').strip()
SINOPAC_SECRET_KEY = os.environ.get('SINOPAC_SECRET_KEY', '').strip()

# 固定推播 USER ID
LINE_USER_ID = "Uf985a37fdacc691e3524e68d2cf68511"

EXCLUDE_WORDS = ["爆料", "同學會", "達人", "無腦", "學堂", "康和", "券商分點", "存股"]
THIN_LINE = "─────────────"

def get_last_trading_day():
    now_tw = datetime.now(timezone(timedelta(hours=8)))
    weekday = now_tw.weekday()
    if weekday == 5:
        now_tw -= timedelta(days=1)
    elif weekday == 6:
        now_tw -= timedelta(days=2)
    return now_tw

def get_price_twse(sid):
    try:
        last_day = get_last_trading_day()
        date_str = last_day.strftime("%Y%m%d")
        url = "https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date=" + date_str + "&stockNo=" + sid
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        rows = data.get("data", [])
        if not rows:
            return None, None
        last = rows[-1]
        p = float(str(last[6]).replace(",", ""))
        chg = float(str(last[6]).replace(",", "")) - float(str(last[5]).replace(",", ""))
        return p, chg
    except Exception as e:
        print("TWSE failed " + sid + ": " + str(e))
        return None, None

def get_price_tpex(sid):
    try:
        last_day = get_last_trading_day()
        roc_year = last_day.year - 1911
        ym = str(roc_year) + "/" + last_day.strftime("%m")
        url = "https://www.tpex.org.tw/web/stock/aftertrading/daily_trading_info/st43_result.php?l=zh-tw&d=" + ym + "&s=" + sid + "&o=json"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        rows = data.get("aaData", [])
        if not rows:
            return None, None
        last = rows[-1]
        p = float(str(last[6]).replace(",", ""))
        prev = float(str(last[5]).replace(",", "")) if last[5] != "--" else p
        chg = round(p - prev, 2)
        return p, chg
    except Exception as e:
        print("TPEX failed " + sid + ": " + str(e))
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
        print("shioaji failed " + sid + ": " + str(e))
        return None, None

def get_price(api, sid, exchange):
    p, chg = get_price_shioaji(api, sid)
    if p and p > 0:
        return p, chg
    if exchange == "OTC":
        p, chg = get_price_tpex(sid)
    else:
        p, chg = get_price_twse(sid)
    return p, chg

def get_news(stock_name, stock_id, max_news=2):
    try:
        query = stock_name + " " + stock_id
        url = "https://news.google.com/rss/search?q=" + query + "&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        root = ET.fromstring(r.content)
        items = root.findall(".//item")
        news_list = []
        now_tw = datetime.now(timezone(timedelta(hours=8)))

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

def job():
    # 找觀察清單 Excel 檔案
    excel_files = glob.glob("*.xlsx")
    if not excel_files:
        print("no excel found")
        return

    target_file = next((f for f in excel_files if "觀察清單" in f), None)
    if not target_file:
        print("找不到觀察清單檔案")
        return
    print("reading: " + target_file)

    df_watch = pd.read_excel(target_file, sheet_name="觀察清單", dtype={'代號': str})
    df_watch = df_watch.dropna(subset=['代號', '名稱'])

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
        sid = str(row['代號']).strip()
        name = str(row['名稱']).strip()
        exchange = str(row.get('交易所', 'TSE')).strip()
        cost_226 = float(str(row['2026/2/26收盤價']).replace(',', ''))
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

            if cost_226 > 0:
                growth = (p - cost_226) / cost_226 * 100
                growth_sign = "+" if growth >= 0 else ""
                growth_arrow = "↑" if growth >= 0 else "↓"
                report += "  2/26:" + "{:.2f}".format(cost_226) + "  " + growth_arrow + " " + growth_sign + "{:.2f}".format(growth) + "%\n"
        else:
            report += "  價格取得失敗\n"

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

if __name__ == "__main__":
    job()
