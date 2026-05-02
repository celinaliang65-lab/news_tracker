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
LINE_USER_ID = "Uf985a37fdacc691e3524e68d2cf68511"
SINOPAC_API_KEY = os.environ.get('SINOPAC_API_KEY', '').strip()
SINOPAC_SECRET_KEY = os.environ.get('SINOPAC_SECRET_KEY', '').strip()

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

def get_monthly_revenue(sid):
    try:
        now_tw = datetime.now(timezone(timedelta(hours=8)))
        # 抓最近兩個月確保有資料
        for months_back in [1, 2]:
            check_date = now_tw - timedelta(days=30 * months_back)
            roc_year = check_date.year - 1911
            month = check_date.month
            url = "https://mops.twse.com.tw/mops/web/ajax_t05st10_ifrs"
            data = {
                "encodeURIComponent": "1",
                "step": "1",
                "firstin": "1",
                "off": "1",
                "keyword4": "",
                "code1": "",
                "TYPEK2": "",
                "checkbtn": "",
                "queryName": "co_id",
                "inpuType": "co_id",
                "TYPEK": "all",
                "isnew": "false",
                "co_id": sid,
                "year": str(roc_year),
                "month": str(month).zfill(2)
            }
            headers = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/x-www-form-urlencoded"}
            r = requests.post(url, data=data, headers=headers, timeout=15)
            r.encoding = "utf-8"

            if "查無資料" in r.text or len(r.text) < 100:
                continue

            # 解析月營收
            import re
            # 找當月營收數字
            pattern = r'<td[^>]*>[\s]*([\d,]+)[\s]*</td>'
            matches = re.findall(pattern, r.text)
            if len(matches) >= 2:
                current = float(matches[0].replace(",", "")) / 1000  # 轉成億
                last_year = float(matches[1].replace(",", "")) / 1000
                yoy = (current - last_year) / last_year * 100 if last_year != 0 else 0
                month_str = str(check_date.year) + "/" + str(month).zfill(2)
                return month_str, current, yoy
        return None, None, None
    except Exception as e:
        print("revenue failed " + sid + ": " + str(e))
        return None, None, None

def get_eps(sid):
    try:
        now_tw = datetime.now(timezone(timedelta(hours=8)))
        url = "https://mops.twse.com.tw/mops/web/ajax_t163sb04"
        data = {
            "encodeURIComponent": "1",
            "step": "1",
            "firstin": "1",
            "off": "1",
            "keyword4": "",
            "code1": "",
            "TYPEK2": "",
            "checkbtn": "",
            "queryName": "co_id",
            "inpuType": "co_id",
            "TYPEK": "all",
            "isnew": "false",
            "co_id": sid,
            "year": str(now_tw.year - 1911),
        }
        headers = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/x-www-form-urlencoded"}
        r = requests.post(url, data=data, headers=headers, timeout=15)
        r.encoding = "utf-8"

        if "查無資料" in r.text or len(r.text) < 100:
            return None, None

        import re
        # 找EPS數值
        pattern = r'<td[^>]*>(Q[1-4]|第[一二三四]季)[^<]*</td>.*?<td[^>]*>([\d.-]+)</td>'
        matches = re.findall(pattern, r.text, re.DOTALL)
        if matches:
            quarter = matches[-1][0]
            eps = matches[-1][1]
            return quarter, float(eps)
        return None, None
    except Exception as e:
        print("EPS failed " + sid + ": " + str(e))
        return None, None

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

if __name__ == "__main__":
    job()
