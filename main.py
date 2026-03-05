import os
import requests
from datetime import datetime
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

# OKX API - XAU/USDT 永续合约
OKX_URL = "https://www.okx.com/api/v5/market/ticker?instId=XAU-USDT-SWAP"
WEBHOOK = os.environ.get("FEISHU_WEBHOOK")

def push_gold_price():
    print(f"[{datetime.now()}] 开始获取 OKX XAU/USDT 数据...")
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(OKX_URL, headers=headers, timeout=15)
        r.raise_for_status()
        result = r.json()
        
        if result.get('code') != '0':
            raise Exception(f"OKX API 错误: {result.get('msg')}")
        
        data = result.get('data', [{}])[0]
        
        last_price = float(data.get('last', '0'))
        open_24h = float(data.get('open24h', '0'))
        high_24h = float(data.get('high24h', '0'))
        low_24h = float(data.get('low24h', '0'))
        vol_24h = float(data.get('vol24h', '0'))
        
        price_change = last_price - open_24h if open_24h > 0 else 0
        change_pct = (price_change / open_24h * 100) if open_24h > 0 else 0
        
        print(f"获取成功: 价格={last_price}, 涨跌={change_pct:.2f}%")
        
        if last_price == 0:
            msg = "【OKX XAU/USDT】数据异常"
        else:
            emoji = "📈" if price_change >= 0 else "📉"
            msg = f"""⏰ {datetime.now().strftime("%H:%M")}
📊 OKX XAU/USDT 永续:
   最新价: {last_price:.2f} USDT
   涨跌: {emoji} {price_change:+.2f} ({change_pct:+.2f}%)
   最高: {high_24h:.2f} / 最低: {low_24h:.2f}
   成交量: {vol_24h:.4f} XAU"""
    except Exception as e:
        msg = f"【OKX XAU/USDT】数据获取失败: {str(e)}"
        print(f"获取失败: {e}")
    
    try:
        if WEBHOOK:
            payload = {"msg_type": "text", "content": {"text": f"【黄金监控 - OKX】\n{msg}"}}
            resp = requests.post(WEBHOOK, json=payload, timeout=10)
            print(f"推送成功: {resp.status_code}")
        else:
            print("错误: 未设置 FEISHU_WEBHOOK")
    except Exception as e:
        print(f"推送失败: {e}")

scheduler = BackgroundScheduler()
scheduler.add_job(push_gold_price, 'cron', minute='0,15,30,45')
scheduler.add_job(push_gold_price, 'date', run_date=datetime.now())
scheduler.start()
print(f"[{datetime.now()}] 定时任务已启动，每15分钟推送一次 OKX 金价")

@app.route('/')
def health_check():
    return {"status": "running", "service": "gold-monitor-okx", "time": datetime.now().isoformat()}

@app.route('/trigger')
def manual_trigger():
    push_gold_price()
    return {"status": "triggered"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
