import os
import requests
from datetime import datetime
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

OKX_URL = "https://www.okx.com/api/v5/market/ticker?instId=XAU-USDT-SWAP"
WEBHOOK = os.environ.get("FEISHU_WEBHOOK")

def push_okx_price():
    now = datetime.now().strftime("%H:%M")
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(OKX_URL, headers=headers, timeout=10)
        r.raise_for_status()
        result = r.json()
        
        if result.get('code') != '0':
            raise Exception(f"API错误: {result.get('msg')}")
        
        data = result.get('data', [{}])[0]
        last_price = float(data.get('last', '0'))
        open_24h = float(data.get('open24h', '0'))
        
        change = last_price - open_24h if open_24h > 0 else 0
        change_pct = (change / open_24h * 100) if open_24h > 0 else 0
        
        emoji = "📈" if change >= 0 else "📉"
        
        msg = f"""⏰ {now}
💰 OKX金: {last_price:.2f} USDT {emoji} {change:+.2f} ({change_pct:+.2f}%)"""
        
    except Exception as e:
        msg = f"⏰ {now}\n💰 OKX金: 获取失败 ({str(e)})"
    
    try:
        if WEBHOOK:
            payload = {
                "msg_type": "text", 
                "content": {"text": f"【OKX监控】\n{msg}"}
            }
            resp = requests.post(WEBHOOK, json=payload, timeout=10)
            print(f"[{now}] OKX推送成功: {resp.status_code}")
        else:
            print("错误: 未设置 FEISHU_WEBHOOK")
    except Exception as e:
        print(f"推送失败: {e}")

scheduler = BackgroundScheduler()
scheduler.add_job(push_okx_price, 'cron', minute='0,15,30,45')
scheduler.add_job(push_okx_price, 'date', run_date=datetime.now())
scheduler.start()

print(f"[{datetime.now()}] OKX监控已启动，每15分钟推送")

@app.route('/')
def health_check():
    return {"status": "running", "service": "okx-monitor", "time": datetime.now().isoformat()}

@app.route('/trigger')
def manual_trigger():
    push_okx_price()
    return {"status": "triggered"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
