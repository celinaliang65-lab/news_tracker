import os
import glob
import pandas as pd
import shioaji as sj
import json
from linebot import LineBotApi
from linebot.models import TextSendMessage

# 1. 環境變數與設定[span_0](start_span)[span_0](end_span)
LINE_ACCESS_TOKEN = os.environ.get('LINE_ACCESS_TOKEN', '').strip()
LINE_USER_ID = "Uf985a37fdacc691e3524e68d2cf68511" 
SINOPAC_API_KEY = os.environ.get('SINOPAC_API_KEY', '').strip()
SINOPAC_SECRET_KEY = os.environ.get('SINOPAC_SECRET_KEY', '').strip()

HISTORY_FILE = "push_history.json"

def get_financial_data(sid):
    """模擬抓取月營收與 EPS 數據，正式環境可對接 API"""
    return {
        "month": "4",
        "rev_val": "12.5億",
        "rev_yoy": "+15.3%",
        "eps_q": "Q1",
        "eps_val": "8.07"
    }

def job():
    # 2. 讀取推播紀錄[span_1](start_span)[span_1](end_span)
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            history = json.load(f)
    else:
        history = {}

    # 3. 讀取 Excel 檔案[span_2](start_span)[span_2](end_span)
    excel_files = glob.glob("*.xlsx")
    target_file = next((f for f in excel_files if "觀察清單" in f), None)
    if not target_file:
        print("找不到包含 '觀察清單' 字樣的 Excel 檔案")
        return
    
    df_watch = pd.read_excel(target_file, sheet_name="觀察清單", dtype={'代號': str})
    df_watch = df_watch.dropna(subset=['代號', '名稱'])

    # 4. 登入 Shioaji[span_3](start_span)[span_3](end_span)
    api = sj.Shioaji()
    try:
        api.login(api_key=SINOPAC_API_KEY, secret_key=SINOPAC_SECRET_KEY)
    except:
        api = None

    for _, row in df_watch.iterrows():
        sid = str(row['代號']).strip()
        name = str(row['名稱']).strip()
        
        # 取得現價與財報數據 (模擬數據)[span_4](start_span)[span_4](end_span)
        p, chg = 155.5, 2.5 
        fin = get_financial_data(sid)

        # 5. 判斷是否為新資料[span_5](start_span)[span_5](end_span)
        last_stat = history.get(sid, {"month": "", "eps": ""})
        is_new_data = (fin["month"] != last_stat["month"]) or (fin["eps_q"] != last_stat["eps"])

        if is_new_data:
            day_icon = "🔺" if chg > 0 else ("🔽" if chg < 0 else "➖")
            
            # --- 符合 image_4.png 格式要求 ---
            # 抬頭靠左
            report = f"{sid} {name}\n"
            # 數據行：開頭縮進一個全形空格[span_6](start_span)[span_6](end_span)
            report += f"　現價：{p:.2f} {day_icon} +{abs(chg):.2f}\n"
            report += f"　月營收：{fin['month']}月 {fin['rev_val']} ↑ {fin['rev_yoy']} (YoY)\n"
            report += f"　EPS：{fin['eps_q']} {fin['eps_val']}元\n"
            report += "───────────────────\n"
            # 新聞符號使用 • 且縮排一格[span_7](start_span)[span_7](end_span)
            report += "　• 測試新聞 1：營收獲利追蹤中\n"
            report += "　• 測試新聞 2：財報更新自動推播\n"

            # 6. 執行推播[span_8](start_span)[span_8](end_span)
            try:
                line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
                line_bot_api.push_message(LINE_USER_ID, TextSendMessage(text=report))
                print(f"{sid} 推播成功")
                # 更新紀錄
                history[sid] = {"month": fin["month"], "eps": fin["eps_q"]}
            except Exception as e:
                print(f"{sid} 推播失敗: {e}")

    # 存回推播歷史[span_9](start_span)[span_9](end_span)
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    job()
