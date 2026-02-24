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
    # Wir nutzen ein system_instruction, um die KI stabiler zu machen
    model = genai.GenerativeModel('gemini-1.5-flash')

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except: pass

# --- 2. TICKER-LISTE (Optimiert auf Stabilität) ---
def get_tickers():
    # .F steht für Frankfurt (oft stabiler bei Yahoo als .DE/Xetra)
    de_list = [
        "PNTX.F", "PTP.F", "DFTK.F", "PZNA.F", "SZA.F", "EON.F", "MOR.F", "VAR1.F", "SOW.F", # Sorgenkinder gefixt
        "SAP.DE", "SIE.DE", "DTE.DE", "AIR.DE", "ALV.DE", "MBG.DE", "BMW.DE", "BAS.DE", "DHL.DE", 
        "VOW3.DE", "BAYN.DE", "RHM.DE", "IFX.DE", "MRK.DE", "BEI.DE", "MTX.DE", "DB1.DE", "CBK.DE", 
        "DBK.DE", "ADS.DE", "HEI.DE", "CON.DE", "HEN3.DE", "SY1.DE", "VNA.DE", "RWE.DE", "DTG.DE", 
        "MUV2.DE", "ZAL.DE", "HNR1.DE", "QIA.DE", "FRE.DE", "FME.DE", "SHL.DE", "BNR.DE", "KGX.DE", 
        "PUM.DE", "LEG.DE", "TAG.DE", "FRA.DE", "G1A.DE", "LHA.DE", "EVK.DE", "LAN.DE", "SDF.DE", 
        "HLE.DE", "TKWY.DE", "SYAB.DE", "AFX.DE", "HOT.DE", "NDX1.DE", "JEN.DE", "AIXA.DE", "EVT.DE", 
        "BOSS.DE", "BC8.DE", "WAF.DE", "FPE3.DE", "FNTN.DE", "BVB.DE", "TKA.DE", "GXI.DE", "UTDI.DE", 
        "1U1.DE", "SMHN.DE", "PBB.DE", "GFT.DE", "O2D.DE", "ADV.DE", "ETL.DE", "LXS.DE", "JUN3.DE", 
        "KRN.DE", "GBF.DE", "HDD.DE", "AM3D.DE", "GLJ.DE", "PSM.DE", "NOEJ.DE", "AOX.DE", "HBH.DE", "DUE.DE"
    ]

    us_list = [
        "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK-B", "LLY", "AVGO",
        "DELL", "V", "JPM", "MA", "UNH", "HD", "PG", "COST", "NFLX", "ABBV", "ADBE",
        "CRM", "ORCL", "AMD", "BAC", "PEP", "KO", "CVX", "XOM", "TMO", "WMT",
        "DIS", "INTC", "CSCO", "VZ", "PFE", "NKE", "INTU", "QCOM", "TXN", "AMAT",
        "ISRG", "BKNG", "MU", "PANW", "GILD", "LRCX", "SBUX", "PYPL", "SNPS", "CDNS"
    ]

    return list(set(de_list + us_list))

# --- 3. SCREENER ---
def run_sentinel():
    print(f"🚀 Scan Start: {datetime.now()}")
    all_tickers = get_tickers()
    
    # Download mit Fehler-Handling
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
            
            if rel_vol > 1.5 and close > sma_50:
                signals.append({'Ticker': ticker, 'Price': round(close, 2), 'Vol': round(rel_vol, 1)})
        except: continue

    if signals:
        for s in signals:
            try:
                # Optimierter Prompt: KI soll immer antworten
                prompt = (f"Analysiere die Aktie {s['Ticker']}. Sie hat ein hohes Volumen ({s['Vol']}x). "
                          f"Nenne kurz den Hauptgrund (News von heute/gestern) oder die charttechnische Lage. "
                          f"Antworte in maximal 2 Sätzen auf Deutsch.")
                
                response = model.generate_content(prompt)
                ki_text = response.text.strip() if response.text else "Keine News gefunden, aber technischer Ausbruch."
                
                msg = f"🎯 *SIGNAL: {s['Ticker']}*\n💰 Preis: {s['Price']}€\n📊 Vol: {s['Vol']}x\n🤖 KI: {ki_text}"
                send_telegram_msg(msg)
            except Exception as e:
                print(f"KI Fehler für {s['Ticker']}: {e}")
                send_telegram_msg(f"🎯 *SIGNAL: {s['Ticker']}*\n💰 Preis: {s['Price']}€\n📊 Vol: {s['Vol']}x")
    
    send_telegram_msg(f"✅ *Sentinel Scan beendet*\n🔢 Geprüft: {len(all_tickers)} Aktien\n🎯 Signale: {len(signals)}")

if __name__ == "__main__":
    run_sentinel()
