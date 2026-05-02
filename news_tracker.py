import json
import os

# 1. 記憶機制：確保不重複推播
HISTORY_FILE = "push_history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def job():
    history = load_history()
    # ... (Excel 讀取與 shioaji 登入) ...[span_12](start_span)[span_12](end_span)

    for _, row in df_watch.iterrows():
        sid = str(row['代號']).strip()
        name = str(row['名稱']).strip()
        
        # 取得數據 (優先使用 shioaji，備援使用爬蟲)[span_13](start_span)[span_13](end_span)
        p, chg = get_price(api, sid, exchange) 
        fin = fetch_financial_data(sid) # 包含 month, eps_q 等

        # 2. 判斷是否有新資料[span_14](start_span)[span_14](end_span)
        last_stat = history.get(sid, {"month": "", "eps": ""})
        if fin["month"] != last_stat["month"] or fin["eps_q"] != last_stat["eps"]:
            
            # 3. 依照指定格式組合報表
            day_icon = "🔺" if chg > 0 else ("🔽" if chg < 0 else "➖")[span_15](start_span)[span_15](end_span)
            
            report = f"{sid} {name}\n" # 抬頭靠左
            report += f"　現價：{p:.2f} {day_icon} {abs(chg):.2f}\n" # 縮排一格[span_16](start_span)[span_16](end_span)
            report += f"　月營收：{fin['month']}月 {fin['rev_val']} ↑ {fin['rev_yoy']} (YoY)\n"
            report += f"　EPS：{fin['eps_q']} {fin['eps_val']}元\n"
            report += "───────────────────\n"
            
            # 4. 新聞列表格式化[span_17](start_span)[span_17](end_span)
            news_list = get_news(name, sid)
            for news in news_list:
                report += f"　• {news}\n" # 縮排一格並使用 • 符號

            # 5. 發送推播並更新紀錄[span_18](start_span)[span_18](end_span)
            LineBotApi(LINE_ACCESS_TOKEN).push_message(LINE_USER_ID, TextSendMessage(text=report))
            history[sid] = {"month": fin["month"], "eps": fin["eps_q"]}

    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=4)
