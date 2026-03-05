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
        
        # 解析格式: v_hf_GC="5108.91,-0.50,5111.80,5113.50,5204.30,5085.50,21:25:10..."
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
    
    # 并行获取三个数据源
    rtj = fetch_rtj_gold()
    tencent = fetch_tencent_gold()
    okx = fetch_okx_gold()
    
    # 构建消息
    lines = [f"⏰ {now}"]
    
    # 融通金
    if rtj['success']:
        lines.append(f"💰 融通金: {rtj['price']}元/g")
    else:
        lines.append(f"💰 融通金: 获取失败 ({rtj.get('error', '未知错误')})")
    
    # 现货黄金（腾讯）
    if tencent['success']:
        change_str = format_change(tencent['change_pct'], is_pct=True)
