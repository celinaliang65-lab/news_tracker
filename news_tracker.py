# 確保 day_icon 邏輯正確
day_icon = "🔺" if chg > 0 else ("🔽" if chg < 0 else "➖")

# 1. 股票抬頭：靠左對齊，完全不加星號[span_1](start_span)[span_1](end_span)
report = f"{sid} {name}\n"

# 2. 數據行：開頭縮排「一個」全形空格[span_2](start_span)[span_2](end_span)
# 這裡我只放了一個全形空格 　
report += f"　現價：{p:.2f} {day_icon} +{abs(chg):.2f}\n"
report += f"　月營收：{fin['month']}月 {fin['rev_val']} ↑ {fin['rev_yoy']} (YoY)\n"
report += f"　EPS：{fin['eps_q']} {fin['eps_val']}元\n"

# 3. 分隔線[span_3](start_span)[span_3](end_span)
report += "───────────────────\n"

# 4. 新聞列表：開頭縮排「一個」全形空格，符號使用 •[span_4](start_span)[span_4](end_span)
news_list = get_news(name, sid)
if news_list:
    for news in news_list:
        # 同樣只縮排一個全形空格
        report += f"　• {news}\n"
else:
    report += "　• 暫無相關新聞\n"

# 5. 推播並記錄歷史 (避免重複發送)
try:
    line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
    line_bot_api.push_message(LINE_USER_ID, TextSendMessage(text=report))
    history[sid] = {"month": fin["month"], "eps": fin["eps_q"]}
except Exception as e:
    print(f"推播失敗: {e}")
