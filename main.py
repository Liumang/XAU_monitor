import os
import requests
import json
from datetime import datetime
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

BINANCE_URL = "https://gold-api.61710284.workers.dev/fapi/v1/ticker/24hr?symbol=XAUUSDT"
WEBHOOK = os.environ.get("FEISHU_WEBHOOK")

def push_gold_price():
    """获取币安金价并推送到飞书"""
    print(f"[{datetime.now()}] 开始获取币安 XAU/USDT 数据...")
    
    try:
        r = requests.get(BINANCE_URL, timeout=15)
        r.raise_for_status()
        d = r.json()
        
        price = float(d.get("lastPrice", "0"))
        change = float(d.get("priceChange", "0"))
        change_pct = float(d.get("priceChangePercent", "0"))
        high = float(d.get("highPrice", "0"))
        low = float(d.get("lowPrice", "0"))
        
        print(f"获取成功: 价格={price}, 涨跌={change_pct}%")
        
        if price == 0:
            msg = "【币安XAU/USDT】数据异常"
        else:
            emoji = "📈" if change >= 0 else "📉"
            msg = f"""⏰ {datetime.now().strftime("%H:%M")}
📊 币安 XAU/USDT 永续:
   最新价: {price:.2f} USDT
   涨跌: {emoji} {change:+.2f} ({change_pct:+.2f}%)
   最高: {high:.2f} / 最低: {low:.2f}"""
    except Exception as e:
        msg = f"【币安XAU/USDT】数据获取失败: {str(e)}"
        print(f"获取失败: {e}")
    
    try:
        if WEBHOOK:
            payload = {"msg_type": "text", "content": {"text": f"【币安黄金监控】\n{msg}"}}
            resp = requests.post(WEBHOOK, json=payload, timeout=10)
            print(f"推送成功: {resp.status_code}")
        else:
            print("错误: 未设置 FEISHU_WEBHOOK")
    except Exception as e:
        print(f"推送失败: {e}")

# 创建定时任务调度器
scheduler = BackgroundScheduler()

# 每15分钟执行一次
scheduler.add_job(push_gold_price, 'cron', minute='0,15,30,45')

# 启动时立即执行一次
scheduler.add_job(push_gold_price, 'date', run_date=datetime.now())

scheduler.start()
print(f"[{datetime.now()}] 定时任务已启动，每15分钟推送一次币安金价")

@app.route('/')
def health_check():
    """健康检查端点"""
    return {
        "status": "running",
        "service": "gold-monitor",
        "time": datetime.now().isoformat()
    }

@app.route('/trigger')
def manual_trigger():
    """手动触发推送"""
    push_gold_price()
    return {"status": "triggered"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
