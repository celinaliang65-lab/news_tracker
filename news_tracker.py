import json
import os

# 1. 狀態記憶檔案 (會存在 GitHub 運行的當前目錄下)
HISTORY_FILE = "push_history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_history(history):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=4)

def job():
    history = load_history()
    # ... (Excel 讀取與 shioaji 登入邏輯保持不變) ...[span_5](start_span)[span_5](end_span)

    for _, row in df_watch.iterrows():
        sid = str(row['代號']).strip()
        name = str(row['名稱']).strip()
        exchange = str(row.get('交易所', 'TSE')).strip()

        # 2. 抓取現價與漲跌 (沿用原有的 get_price 函式)[span_6](start_span)[span_6](end_span)
        p, chg = get_price(api, sid, exchange) 
        
        # 3. 抓取最新財報 (從 shioaji 或備援 API)
        # 範例數據：curr_rev_m="4", curr_eps_q="Q1" 等
        fin = fetch_financial_data(sid) 

        # 4. 比對歷史紀錄：是否有新月份或新季度？[span_7](start_span)[span_7](end_span)
        last_stat = history.get(sid, {"month": "", "eps": ""})
        is_new_data = (fin["month"] != last_stat["month"]) or (fin["eps_q"] != last_stat["eps"])

        if is_new_data:
            day_icon = "🔺" if chg > 0 else ("🔽" if chg < 0 else "➖")[span_8](start_span)[span_8](end_span)
            
            # --- 格式化報表 ---
            # 抬頭靠左
            report = f"{sid} {name}\n" 
            # 數據行：開頭縮進一個全形空格[span_9](start_span)[span_9](end_span)
            report += f"　現價：{p:.2f} {day_icon} {abs(chg):.2f}\n[span_10](start_span)"[span_10](end_span)
            report += f"　月營收：{fin['month']}月 {fin['rev_val']} ↑ {fin['rev_yoy']} (YoY)\n[span_11](start_span)"[span_11](end_span)
            report += f"　EPS：{fin['eps_q']} {fin['eps_val']}元\n[span_12](start_span)"[span_12](end_span)
            report += "───────────────────\n"
            
            # 5. 新聞列表：開頭縮進一格並使用 • 符號[span_13](start_span)[span_13](end_span)
            news_list = get_news(name, sid)
            for news in news_list:
                report += f"　• {news}\n[span_14](start_span)"[span_14](end_span)

            # 6. 執行推播並更新紀錄[span_15](start_span)[span_15](end_span)
            try:
                LineBotApi(LINE_ACCESS_TOKEN).push_message(LINE_USER_ID, TextSendMessage(text=report))
                history[sid] = {"month": fin["month"], "eps": fin["eps_q"]}[span_16](start_span)[span_16](end_span)
            except Exception as e:
                print(f"LINE 推播失敗: {e}")

    save_history(history)
