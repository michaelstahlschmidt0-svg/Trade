import os
import yfinance as yf
import pandas as pd
import google.generativeai as genai
import requests
from datetime import datetime

# --- 1. KONFIGURATION ---
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel('models/gemini-1.5-flash')

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except: pass

# --- 2. MODUL: TICKER & SCREENING ---
def get_tickers():
    # Notfall-Liste + Deine Favoriten
    all_tickers = ["PNTX.DE", "PZNA.DE", "SZA.DE", "SAP.DE", "DTE.DE"]
    headers = {'User-Agent': 'Mozilla/5.0'}
    for idx in ["DAX", "MDAX", "SDAX"]:
        try:
            url = f"https://de.wikipedia.org/wiki/Liste_der_im_{idx}_gelisteten_Unternehmen"
            html = requests.get(url, headers=headers, timeout=10).text
            tables = pd.read_html(html)
            for df in tables:
                col = next((c for c in df.columns if 'Symbol' in str(c) or 'Kürzel' in str(c)), None)
                if col:
                    all_tickers.extend([f"{s}.DE" for s in df[col].dropna().tolist() if ".DE" not in str(s)])
                    break
        except: continue
    return list(set(all_tickers))

def screen_market(tickers):
    found = []
    # Lade Daten für den letzten Monat
    data = yf.download(tickers, period="60d", interval="1d", group_by='ticker', progress=False)
    
    for ticker in tickers:
        try:
            df = data[ticker].dropna()
            if len(df) < 30: continue
            
            close = df['Close'].iloc[-1]
            # Volumen-Check: Heute vs. 20-Tage Durchschnitt
            avg_vol = df['Volume'].rolling(20).mean().iloc[-1]
            rel_vol = df['Volume'].iloc[-1] / avg_vol
            # Trend-Check: Über dem 50-Tage Durchschnitt
            sma_50 = df['Close'].rolling(50).mean().iloc[-1]
            
            # DIE FILTER-LOGIK (Nur starke Ausbrüche)
            if rel_vol > 1.8 and close > sma_50:
                found.append({'Ticker': ticker, 'Price': round(close, 2), 'Vol': round(rel_vol, 1)})
        except: continue
    return found

# --- 3. HAUPTLOGIK ---
def run_sentinel():
    print(f"🚀 Sentinel Scan Start: {datetime.now()}")
    tickers = get_tickers()
    signals = screen_market(tickers)
    
    if signals:
        for s in signals:
            prompt = f"Analysiere Aktie {s['Ticker']}. Warum könnte das Volumen heute {s['Vol']}x höher sein? Suche News 2026. 1 Satz."
            try:
                res = model.generate_content(prompt)
                msg = f"🎯 *AUSBRUCH GEFUNDEN*\n\n📟 *Aktie:* {s['Ticker']}\n💰 *Preis:* {s['Price']}€\n📊 *Volumen:* {s['Vol']}x\n🤖 *KI:* {res.text}"
                send_telegram_msg(msg)
            except: pass
    
    # Der tägliche Heartbeat
    heartbeat = f"✅ *Scan abgeschlossen*\n🔢 Geprüft: {len(tickers)} Aktien\n🎯 Signale: {len(signals)}"
    send_telegram_msg(heartbeat)

if __name__ == "__main__":
    run_sentinel()
