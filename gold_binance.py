import os
import requests
import json
from datetime import datetime

BINANCE_URL = "https://fapi.binance.com/fapi/v1/ticker/24hr?symbol=XAUUSDT"
WEBHOOK = os.environ.get("FEISHU_WEBHOOK")

def main():
    try:
        r = requests.get(BINANCE_URL, timeout=15)
        r.raise_for_status()
        d = r.json()
        
        print("API Response:", json.dumps(d, indent=2))
        
        price = float(d.get("lastPrice", "0"))
        change = float(d.get("priceChange", "0"))
        change_pct = float(d.get("priceChangePercent", "0"))
        high = float(d.get("highPrice", "0"))
        low = float(d.get("lowPrice", "0"))
        
        if price == 0:
            msg = "【币安XAU/USDT】数据异常，价格获取失败"
        else:
            emoji = "📈" if change >= 0 else "📉"
            msg = f"""⏰ {datetime.now().strftime("%H:%M")}
📊 币安 XAU/USDT 永续:
   最新价: {price:.2f} USDT
   涨跌: {emoji} {change:+.2f} ({change_pct:+.2f}%)
   最高: {high:.2f} / 最低: {low:.2f}"""
    except Exception as e:
        msg = f"【币安XAU/USDT】数据获取失败: {str(e)}"
        print(f"Error: {e}")
    
    try:
        payload = {"msg_type": "text", "content": {"text": f"【币安黄金】\n{msg}"}}
        resp = requests.post(WEBHOOK, json=payload, timeout=10)
        print(f"Webhook response: {resp.status_code}, {resp.text}")
    except Exception as e:
        print(f"Webhook error: {e}")

if __name__ == "__main__":
    main()
