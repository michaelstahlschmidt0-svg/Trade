import os
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime
import time

# --- 1. KONFIGURATION ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try: requests.post(url, json=payload, timeout=10)
    except: pass

# --- 2. TICKER-LISTE (Manuell bereinigt) ---
def get_tickers():
    # Korrigierte Ticker (z.B. EOAN statt EON) und Entfernung von Delistings (Varta)
    de_list = [
        "SAP.DE", "SIE.DE", "DTE.DE", "AIR.DE", "ALV.DE", "MBG.DE", "BMW.DE", "BAS.DE", "DHL.DE", 
        "VOW3.DE", "BAYN.DE", "RHM.DE", "IFX.DE", "MRK.DE", "BEI.DE", "MTX.DE", "DB1.DE", "CBK.DE", 
        "DBK.DE", "ADS.DE", "HEI.DE", "CON.DE", "HEN3.DE", "SY1.DE", "VNA.DE", "EOAN.DE", "RWE.DE", 
        "DTG.DE", "MUV2.DE", "ZAL.DE", "HNR1.DE", "QIA.DE", "FRE.DE", "FME.DE", "SHL.DE", "BNR.DE", 
        "KGX.DE", "PUM.DE", "LEG.DE", "FRA.DE", "G1A.DE", "LHA.DE", "EVK.DE","TKA.DE", 
        "SDF.DE", "HLE.DE", "AFX.DE", "HOT.DE", "NDX1.DE", "JEN.DE", "AIXA.DE", "HBH.DE", "DUE.DE", 
        "EVT.DE", "BOSS.DE", "BC8.DE", "WAF.DE", "FPE3.DE", "FNTN.DE", "BVB.DE", "GXI.DE", "PAT.DE", 
        "UTDI.DE", "1U1.DE", "SMHN.DE", "PBB.DE", "GFT.DE", "O2D.HM", "ADV.DE", "ETS.VI", "LXS.DE", 
        "JUN3.DE", "KRN.DE", "GBF.DE", "HDD.DE", "GLJ.DE", "PSM.DE", "NOEJ.DE", 
        
    ]
    us_list = [
        "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK-B", "LLY", "AVGO",
        "DELL", "V", "JPM", "MA", "UNH", "HD", "PG", "COST", "NFLX", "ABBV", "ADBE",
        "CRM", "ORCL", "AMD", "BAC", "PEP", "KO", "CVX", "XOM", "TMO", "WMT",
        "DIS", "INTC", "CSCO", "VZ", "PFE", "NKE", "INTU", "QCOM", "TXN", "JTKWY", "AMAT"
    ]
    return list(set(de_list + us_list))

# --- 3. SCREENER ---
def run_sentinel():
    all_tickers = get_tickers()
    signals = []
    failed = []

    for ticker in all_tickers:
        try:
            t = yf.Ticker(ticker)
            df = t.history(period="60d")
            
            if df.empty or len(df) < 20:
                failed.append(ticker)
                continue

            close = df['Close'].iloc[-1]
            avg_vol = df['Volume'].rolling(20).mean().iloc[-1]
            current_vol = df['Volume'].iloc[-1]
            rel_vol = current_vol / avg_vol
            sma_50 = df['Close'].rolling(50).mean().iloc[-1]
            
            # Signal-Logik: Relatives Volumen > 1.5x und Kurs über SMA 50
            if rel_vol > 1.5 and close > sma_50:
                signals.append({'Ticker': ticker, 'Price': round(close, 2), 'Vol': round(rel_vol, 1)})
            
            time.sleep(0.1) 
        except:
            failed.append(ticker)

    for s in signals:
        # Direkter Link zu TradingView für die manuelle News-Prüfung
        tv_ticker = s['Ticker'].replace(".DE", "").replace(".F", "")
        msg = (f"🎯 *SIGNAL: {s['Ticker']}*\n"
               f"💰 Preis: {s['Price']}€\n"
               f"📊 Vol: {s['Vol']}x\n"
               f"🔗 [Chart & News (TV)](https://de.tradingview.com/symbols/{tv_ticker}/)")
        send_telegram_msg(msg)

    summary = (f"✅ *Sentinel Scan beendet*\n"
               f"🔢 Geprüft: {len(all_tickers)}\n"
               f"❌ Fehler: {len(failed)}\n"
               f"🎯 Signale: {len(signals)}")
    send_telegram_msg(summary)

if __name__ == "__main__":
    run_sentinel()
