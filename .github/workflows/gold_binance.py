import os
import requests
from datetime import datetime

BINANCE_URL = "https://fapi.binance.com/fapi/v1/ticker/24hr?symbol=XAUUSDT"
WEBHOOK = os.environ.get("FEISHU_WEBHOOK")

def get_data():
    try:
        r = requests.get(BINANCE_URL, timeout=15)
        d = r.json()
        return {
            "price": float(d.get("lastPrice", 0)),
            "change": float(d.get("priceChange", 0)),
            "change_pct": float(d.get("priceChangePercent", 0)),
            "high": float(d.get("highPrice", 0)),
            "low": float(d.get("lowPrice", 0)),
        }
    except:
        return None

def main():
    data = get_data()
    if not data:
        msg = "【币安XAU/USDT】数据获取失败"
    else:
        emoji = "📈" if data["change"] >= 0 else "📉"
        msg = f"""⏰ {datetime.now().strftime("%H:%M")}
📊 币安 XAU/USDT 永续:
   最新价: {data['price']:.2f} USDT
   涨跌: {emoji} {data['change']:+.2f} ({data['change_pct']:+.2f}%)
   最高: {data['high']:.2f} / 最低: {data['low']:.2f}"""
    
    payload = {"msg_type": "text", "content": {"text": f"【币安黄金监控】\n{msg}"}}
    requests.post(WEBHOOK, json=payload, timeout=10)
    print("推送完成")

if __name__ == "__main__":
    main()
