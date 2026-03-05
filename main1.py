#!/usr/bin/env python3
"""
Railway 金价监控 - 现货金 + OKX
"""

import os
import requests
import re
from datetime import datetime
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
WEBHOOK = os.environ.get("FEISHU_WEBHOOK")

TENCENT_URL = "https://qt.gtimg.cn/q=hf_GC"
OKX_URL = "https://www.okx.com/api/v5/market/ticker?instId=XAU-USDT-SWAP"

def fetch_tencent_gold():
    try:
        response = requests.get(TENCENT_URL, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        response.encoding = 'gbk'
        match = re.search(r'v_hf_GC="([^"]+)"', response.text)
        if match:
            data = match.group(1).split(',')
            if len(data) >= 2:
                return {'price': data[0], 'change_pct': data[1], 'success': True}
        return {'success': False}
    except:
        return {'success': False}

def fetch_okx_gold():
    try:
        response = requests.get(OKX_URL, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        result = response.json()
        if result.get('code') != '0':
            return {'success': False}
        data = result.get('data', [{}])[0]
        last_price = float(data.get('last', '0'))
        open_24h = float(data.get('open24h', '0'))
        change = last_price - open_24h if open_24h > 0 else 0
        change_pct = (change / open_24h * 100) if open_24h > 0 else 0
        return {
            'price': f"{last_price:.2f}",
            'change': change,
            'change_pct': change_pct,
            'success': True
        }
    except:
        return {'success': False}

def push_all_prices():
    now = datetime.now().strftime("%H:%M")
    tencent = fetch_tencent_gold()
    okx = fetch_okx_gold()
    
    lines = [f"⏰ {now}"]
    
    if tencent['success']:
        val = float(tencent['change_pct'])
        emoji = "📈" if val >= 0 else "📉"
        lines.append(f"💰 现货金: {tencent['price']}美元/oz {emoji} {val:+.2f}%")
    else:
        lines.append(f"💰 现货金: 获取失败")
    
    if okx['success']:
        emoji = "📈" if okx['change'] >= 0 else "📉"
        lines.append(f"💰 OKX金: {okx['price']} USDT {emoji} {okx['change']:+.2f} ({okx['change_pct']:+.2f}%)")
    else:
        lines.append(f"💰 OKX金: 获取失败")
    
    msg = "\n".join(lines)
    
    try:
        if WEBHOOK:
            payload = {"msg_type": "text", "content": {"text": f"【金价监控】\n{msg}"}}
            requests.post(WEBHOOK, json=payload, timeout=10)
    except:
        pass

scheduler = BackgroundScheduler()
scheduler.add_job(push_all_prices, 'cron', minute='0,15,30,45')
scheduler.add_job(push_all_prices, 'date', run_date=datetime.now())
scheduler.start()

@app.route('/')
def health_check():
    return {"status": "running"}

@app.route('/trigger')
def manual_trigger():
    push_all_prices()
    return {"status": "triggered"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
