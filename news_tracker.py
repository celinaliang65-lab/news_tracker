import os
import glob
import pandas as pd
import shioaji as sj
import requests
import json
from linebot import LineBotApi
from linebot.models import TextSendMessage

# 1. 基本設定[span_0](start_span)[span_0](end_span)
LINE_ACCESS_TOKEN = os.environ.get('LINE_ACCESS_TOKEN', '').strip()
LINE_USER_ID = "Uf985a37fdacc691e3524e68d2cf68511" # 妳的 LINE ID[span_1](start_span)[span_1](end_span)
SINOPAC_API_KEY = os.environ.get('SINOPAC_API_KEY', '').strip()
SINOPAC_SECRET_KEY = os.environ.get('SINOPAC_SECRET_KEY', '').strip()

HISTORY_FILE = "push_history.json"

def get_financial_data(sid):
    # 這裡預設回傳 4月與 Q1 的範例數據，確保排版測試成功[span_2](start_span)[span_2](end_span)
    return {
        "month": "4",
        "rev_val": "12.5億",
        "rev_yoy": "+15.3%",
        "eps_q": "Q1",
        "eps_val": "8.07"
    }

def job():
    # 2. 讀取 Excel 檔案[span_3](start_span)[span_3](end_span)
    excel_files = glob.glob("*.xlsx")
    target_file = next((f for f in excel_files if "觀察清單" in f), None)
    
    if not target_file:
        print("Error: Excel file not found")
        return
    
    df_watch = pd.read_excel(target_file, sheet_name="觀察清單", dtype={'代號': str})
    df_watch = df_watch.dropna(subset=['代號', '名稱'])

    # 3. 讀取歷史推播紀錄[span_4](start_span)[span_4](end_span)
    history = {}
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            history = json.load(f)

    # 4. 準備推播內容[span_5](start_span)[span_5](end_span)
    # 注意：為了讓妳「現在測試」能看到結果，我暫時拿掉了「重複不推播」的限制
    for _, row in df_watch.iterrows():
        sid = str(row['代號']).strip()
        name = str(row['名稱']).strip()
        
        # 模擬獲取現價與財報 (正式版可替換回 get_price 函式)[span_6](start_span)[span_6](end_span)
        p, chg = 155.5, 2.5 
        fin = get_financial_data(sid)
        day_icon = "🔺" if chg > 0 else ("🔽" if chg < 0 else "➖")

        # --- 依照妳要求的最終格式組合 ---[span_7](start_span)[span_7](end_span)
        report = f"{sid} {name}\n" # 抬頭靠左[span_8](start_span)[span_8](end_span)
        report += f"　現價：{p:.2f} {day_icon} +{abs(chg):.2f}\n" # 開頭空一個全形空格[span_9](start_span)[span_9](end_span)
        report += f"　月營收：{fin['month']}月 {fin['rev_val']} ↑ {fin['rev_yoy']} (YoY)\n" # 開頭空一格[span_10](start_span)[span_10](end_span)
        report += f"　EPS：{fin['eps_q']} {fin['eps_val']}元\n" # 開頭空一格[span_11](start_span)[span_11](end_span)
        report += "───────────────────\n"
        report += "　• 測試新聞 1：數據自動監控中\n" # 使用 • 符號並空一格[span_12](start_span)[span_12](end_span)
        report += "　• 測試新聞 2：財報更新自動推播\n[span_13](start_span)"[span_13](end_span)

        # 5. 發送 LINE 推播[span_14](start_span)[span_14](end_span)
        try:
            line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
            line_bot_api.push_message(LINE_USER_ID, TextSendMessage(text=report))
            print(f"Sent: {sid} {name}")
            # 更新紀錄，供未來比對使用[span_15](start_span)[span_15](end_span)
            history[sid] = {"month": fin["month"], "eps": fin["eps_q"]}
        except Exception as e:
            print(f"LINE Error: {e}")

    # 6. 存回紀錄檔案[span_16](start_span)[span_16](end_span)
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    job()
