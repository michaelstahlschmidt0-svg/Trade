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

# --- 2. TICKER-LISTE ---
def get_tickers():
    # DEUTSCHE WERTE (DAX, MDAX, SDAX + Deine Favoriten)
    de_list = [
        "PNTX.DE", "PTP.DE", "DFTK.DE", "PZNA.DE", "SZA.DE", "SAP.DE", "SIE.DE", "DTE.DE", "AIR.DE", "ALV.DE",
        "MBG.DE", "BMW.DE", "BAS.DE", "DHL.DE", "VOW3.DE", "BAYN.DE", "RHM.DE", "IFX.DE", "MRK.DE", "BEI.DE",
        "MTX.DE", "DB1.DE", "CBK.DE", "DBK.DE", "ADS.DE", "HEI.DE", "CON.DE", "HEN3.DE", "SY1.DE", "VNA.DE",
        "EON.DE", "RWE.DE", "DTG.DE", "MUV2.DE", "ZAL.DE", "HNR1.DE", "QIA.DE", "FRE.DE", "FME.DE", "SHL.DE",
        "BNR.DE", "KGX.DE", "PUM.DE", "LEG.DE", "TAG.DE", "FRA.DE", "G1A.DE", "LHA.DE", "EVK.DE", "LAN.DE",
        "SDF.DE", "HLE.DE", "TKWY.DE", "SYAB.DE", "AFX.DE", "HOT.DE", "NDX1.DE", "JEN.DE", "AIXA.DE", "SOW.DE",
        "EVT.DE", "MOR.DE", "BOSS.DE", "BC8.DE", "WAF.DE", "FPE3.DE", "FNTN.DE", "BVB.DE", "TKA.DE", "GXI.DE",
        "UTDI.DE", "1U1.DE", "SMHN.DE", "PBB.DE", "GFT.DE", "O2D.DE", "ADV.DE", "VAR1.DE", "ETL.DE", "LXS.DE",
        "JUN3.DE", "KRN.DE", "GBF.DE", "HDD.DE", "AM3D.DE", "GLJ.DE", "PSM.DE", "NOEJ.DE", "AOX.DE", "HBH.DE", "DUE.DE"
    ]

    # US WERTE (Top 50)
    us_list = [
        "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "DELL", "BRK-B", "LLY", "AVGO",
        "V", "JPM", "MA", "UNH", "HD", "PG", "COST", "NFLX", "ABBV", "ADBE",
        "CRM", "ORCL", "AMD", "BAC", "PEP", "KO", "CVX", "XOM", "TMO", "WMT",
        "DIS", "INTC", "CSCO", "VZ", "PFE", "NKE", "INTU", "QCOM", "TXN", "AMAT",
        "ISRG", "BKNG", "MU", "PANW", "GILD", "LRCX", "SBUX", "PYPL", "SNPS", "CDNS"
    ]

    return list(set(de_list + us_list))

# --- 3. SCREENER ---
def run_sentinel():
    print(f"🚀 Scan Start: {datetime.now()}")
    all_tickers = get_tickers()
    
    # Download Markt-Daten (60 Tage für SMA50 und Vol-Schnitt)
    data = yf.download(all_tickers, period="60d", interval="1d", group_by='ticker', progress=False)
    
    signals = []
    for ticker in all_tickers:
        try:
            df = data[ticker].dropna()
            if len(df) < 30: continue
            
            close = df['Close'].iloc[-1]
            avg_vol = df['Volume'].rolling(20).mean().iloc[-1]
            current_vol = df['Volume'].iloc[-1]
            rel_vol = current_vol / avg_vol
            sma_50 = df['Close'].rolling(50).mean().iloc[-1]
            
            # SIGNAL-LOGIK: Volumen-Ausbruch & über SMA50
            if rel_vol > 1.5 and close > sma_50:
                signals.append({'Ticker': ticker, 'Price': round(close, 2), 'Vol': round(rel_vol, 1)})
        except: continue

    # Nachrichten-Versand
    if signals:
        for s in signals:
            try:
                # KI Analyse
                prompt = f"Aktie {s['Ticker']} hat heute {s['Vol']}x normales Volumen. Warum? Suche News von heute oder gestern. Antworte in 1 kurzen Satz auf Deutsch."
                res = model.generate_content(prompt)
                
                msg = f"🎯 *SIGNAL: {s['Ticker']}*\n💰 Preis: {s['Price']}€\n📊 Vol: {s['Vol']}x\n🤖 KI: {res.text}"
                send_telegram_msg(msg)
            except: 
                # Falls KI hakt, nur Basis-Info
                send_telegram_msg(f"🎯 *SIGNAL: {s['Ticker']}*\n💰 Preis: {s['Price']}€\n📊 Vol: {s['Vol']}x")
    
    # Abschlussbericht
    send_telegram_msg(f"✅ *Sentinel Scan beendet*\n🔢 Geprüft: {len(all_tickers)} Aktien\n🎯 Signale: {len(signals)}")

if __name__ == "__main__":
    run_sentinel()
