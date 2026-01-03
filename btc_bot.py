import requests
import pandas as pd
import os
import time

# Ayarlar (GitHub Secrets üzerinden tanımlanmalı)
TOKEN = os.getenv("BTC_BOT_TOKEN")
CHAT_ID = os.getenv("BTC_CHAT_ID")

def get_btc_data():
    # OKX üzerinden 4 saatlik BTC verisi çekme
    url = "https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=4H&limit=30"
    r = requests.get(url, timeout=10).json()
    if r.get('code') != '0': return None
    df = pd.DataFrame(r['data'], columns=['ts', 'o', 'h', 'l', 'c', 'vol', 'volCcy', 'volCcyQuote', 'confirm'])
    df[['c', 'h', 'l', 'o']] = df[['c', 'h', 'l', 'o']].astype(float)
    return df[::-1].reset_index(drop=True)

def analyze_market_structure(df):
    """Yükselen Tepeler ve Dipleri (HH/HL) hesaplar"""
    # Son 3 önemli tepe ve dip noktasını basitleştirilmiş şekilde bulalım
    # (Pivots: Bir önceki ve bir sonraki mumdan daha yüksek/alçak olan noktalar)
    highs = df['h'].tolist()
    lows = df['l'].tolist()
    
    # Son iki belirgin tepe ve dip (HH/HL tespiti)
    # df.iloc[-1] = Mevcut mum, df.iloc[-5] = Önceki mumlar
    curr_high = max(highs[-5:])
    prev_high = max(highs[-10:-5])
    curr_low = min(lows[-5:])
    prev_low = min(lows[-10:-5])
    
    score = 0
    structure = ""
    
    if curr_high > prev_high and curr_low > prev_low:
        structure = "✅ YÜKSELEN YAPI (HH / HL)"
        score = 40
    elif curr_high < prev_high and curr_low < prev_low:
        structure = "❌ DÜŞEN YAPI (LH / LL)"
        score = 0
    else:
        structure = "⚖️ YATAY / KARARSIZ"
        score = 20
        
    return structure, score, curr_low

def run_btc_analysis():
    df = get_btc_data()
    if df is None: return
    
    struct_text, struct_score, last_support = analyze_market_structure(df)
    
    # İndikatörler
    close = df['c']
    ema20 = close.ewm(span=20, adjust=False).mean().iloc[-1]
    
    # RSI
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rsi = 100 - (100 / (1 + (gain / loss))).iloc[-1]
    
    current_price = close.iloc[-1]
    
    # Skor Hesaplama (100 üzerinden)
    total_score = struct_score # Market yapısı (40)
    
    # EMA Filtresi (30 puan)
    if current_price > ema20: total_score += 30
    
    # RSI Filtresi (30 puan)
    if 45 < rsi < 65: 
        total_score += 30 # Sağlıklı yükseliş alanı
    elif rsi >= 65: 
        total_score += 15 # Aşırı şişmiş, puan kır
    elif rsi < 40:
        total_score += 5  # Çok zayıf
    
    status = "🚀 GÜÇLÜ BOĞA" if total_score >= 80 else "⚖️ NÖTR / BEKLE" if total_score >= 50 else "🛑 RİSKLİ / AYI"
    
    msg = (f"🌐 *BTC PİYASA ANALİZİ*\n"
           f"━━━━━━━━━━━━━━━\n"
           f"📊 *Güven Skoru:* {total_score}/100\n"
           f"📢 *Durum:* {status}\n\n"
           f"🏛 *Market Yapısı:* {struct_text}\n"
           f"📈 *Fiyat:* {current_price:,.0f} USDT\n"
           f"🛡 *Kritik Destek:* {last_support:,.0f} USDT\n"
           f"📉 *Trend (EMA 20):* {'Üstünde ✅' if current_price > ema20 else 'Altında ❌'}\n"
           f"🌡 *RSI (Güç):* {rsi:.1f}\n"
           f"━━━━━━━━━━━━━━━\n"
           f"💡 *Tavsiye:* {'Altcoin işlemleri için her şey yolunda.' if total_score >= 80 else 'Altcoinlerde sadece %100 hacim artışlarını değerlendirin.' if total_score >= 50 else 'NAKİTTE KALIN. Altcoinler ezilebilir.'}")
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown"
    requests.get(url)

if __name__ == "__main__":
    run_btc_analysis()
