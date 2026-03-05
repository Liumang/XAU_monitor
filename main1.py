#!/usr/bin/env python3
"""
合并版金价监控 - main1.py
监控：融通金 + 现货黄金(腾讯) + OKX XAU/USDT
"""

import os
import requests
import re
from datetime import datetime
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

# Webhook
WEBHOOK = os.environ.get("FEISHU_WEBHOOK")

# 数据源URL
RTJ_URL = "http://beijingrtj.com/admin/get_price5.php"
TENCENT_URL = "https://qt.gtimg.cn/q=hf_GC"
OKX_URL = "https://www.okx.com/api/v5/market/ticker?instId=XAU-USDT-SWAP"


def fetch_rtj_gold():
    """获取北京融通金黄金价格"""
    try:
        timestamp = int(datetime.now().timestamp() * 1000)
        url = f"{RTJ_URL}?t={timestamp}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://beijingrtj.com/index.php'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        data = response.text.strip().split(',')
        if len(data) >= 16:
            return {
                'price': data[2],
                'time': data[16],
                'success': True
            }
        return {'success': False, 'error': '数据格式异常'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def fetch_tencent_gold():
    """获取腾讯财经现货黄金价格 (COMEX黄金)"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(TENCENT_URL, headers=headers, timeout=15)
        response.encoding = 'gbk'
        text = response.text
        
        match = re.search(r'v_hf_GC="([^"]+)"', text)
        if match:
            data = match.group(1).split(',')
            if len(data) >= 2:
                return {
                    'price': data[0],
                    'change_pct': data[1],
                    'success': True
                }
        return {'success': False, 'error': '无法解析数据'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def fetch_okx_gold():
    """获取 OKX XAU/USDT 永续合约价格"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(OKX_URL, headers=headers, timeout=15)
        result = response.json()
        
        if result.get('code') != '0':
            return {'success': False, 'error': result.get('msg', 'API错误')}
        
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
    except Exception as e:
        return {'success': False, 'error': str(e)}


def format_change(value, is_pct=False):
    """格式化涨跌幅显示"""
    try:
        val = float(value)
        if val > 0:
            return f"📈 +{val:.2f}{'%' if is_pct else ''}"
        elif val < 0:
            return f"📉 {val:.2f}{'%' if is_pct else ''}"
        else:
            return "➖"
    except:
        return "➖"


def push_all_prices():
    """获取所有价格并推送到飞书"""
    now = datetime.now().strftime("%H:%M")
    
    rtj = fetch_rtj_gold()
    tencent = fetch_tencent_gold()
    okx = fetch_okx_gold()
    
    lines = [f"⏰ {now}"]
    
    if rtj['success']:
        lines.append(f"💰 融通金: {rtj['price']}元/g")
    else:
        lines.append(f"💰 融通金: 获取失败")
    
    if tencent['success']:
        change_str = format_change(tencent['change_pct'], is_pct=True)
        lines.append(f"💰 现货金: {tencent['price']}美元/oz {change_str}")
    else:
        lines.append(f"💰 现货金: 获取失败")
    
    if okx['success']:
        emoji = "📈" if okx['change'] >= 0 else "📉"
        lines.append(f"💰 OKX金: {okx['price']} USDT {emoji} {okx['change']:+.2f} ({okx['change_pct']:+.2f}%)")
    else:
        lines.append(f"💰 OKX金: 获取失败")
    
    msg = "
".join(lines)
    
    try:
        if WEBHOOK:
            payload = {
                "msg_type": "text",
                "content": {"text": f"【金价监控】
{msg}"}
            }
            resp = requests.post(WEBHOOK, json=payload, timeout=10)
            print(f"[{now}] 推送成功: {resp.status_code}")
        else:
            print("错误: 未设置 FEISHU_WEBHOOK")
    except Exception as e:
        print(f"推送失败: {e}")
    
    print(msg)


scheduler = BackgroundScheduler()
scheduler.add_job(push_all_prices, 'cron', minute='0,15,30,45')
scheduler.add_job(push_all_prices, 'date', run_date=datetime.now())
scheduler.start()
print(f"[{datetime.now()}] 合并版金价监控已启动")


@app.route('/')
def health_check():
    return {"status": "running", "version": "main1.py", "time": datetime.now().isoformat()}


@app.route('/trigger')
def manual_trigger():
    push_all_prices()
    return {"status": "triggered"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
