import pandas as pd
from datetime import datetime

def format_stock_summary(stock_list):
    """
    依照使用者指定的格式產出觀察清單摘要
    """
    now = datetime.now().strftime("%Y/%m/%d %H:%M")
    
    # 1. 標題與日期
    report = f"📰 觀察清單新聞摘要\n{now}\n"
    report += "___________________________________\n\n"
    
    for stock in stock_list:
        # 2. 股票名稱與代號
        report += f"**{stock['code']} {stock['name']}**\n"
        
        # 3. 縮行數據區 (使用全型空格達成縮行效果)
        report += f"　**現價：{stock['price']}**\n"
        report += f"　**月營收：{stock['revenue']}**\n"
        report += f"　**EPS：{stock['eps']}**\n"
        
        # 4. 數據與新聞間的分隔線
        report += "___________________________________\n"
        
        # 5. 移除「新聞」二字的列表
        for news in stock['news_list']:
            report += f"* {news}\n"
        
        # 6. 每隻股票後的空行 (關鍵修正)
        report += "\n"
    
    return report

# 模擬資料結構 (實際執行時可連動您的 Excel 或資料庫)
stocks = [
    {
        "code": "6196", "name": "帆宣", 
        "price": "155.50 ▲ +2.50", "revenue": "4月 12.5億 ↑ +15.3% (YoY)", "eps": "Q1 8.07元",
        "news_list": ["帆宣在手訂單維持高檔，受惠半導體龍頭海外擴廠需求。", "智慧工廠自動化系統切入美系供應鏈，營運動能無虞。"]
    },
    {
        "code": "2330", "name": "台積電", 
        "price": "1000.00 ▲ +15.00", "revenue": "4月 2,360億 ↑ +20.9% (YoY)", "eps": "Q1 8.70元",
        "news_list": ["AI 晶片代工訂單持續強勁，美系大行調升目標價。", "2 奈米技術進度穩定，預計明年量產貢獻營收。"]
    }
]

if __name__ == "__main__":
    final_output = format_stock_summary(stocks)
    print(final_output)
