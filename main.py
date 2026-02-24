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

# --- 2. TICKER-MASCHINE ---
def get_tickers():
    # --- DEUTSCHE POWER-LISTE (ca. 100) ---
    de_list = [
        "PNTX.DE", "PZNA.DE", "SZA.DE", "SAP.DE", "SIE.DE", "DTE.DE", "AIR.DE", "ALV.DE", "MBG.DE", "BMW.DE",
        "BAS.DE", "DHL.DE", "VOW3.DE", "BAYN.DE", "RHM.DE", "IFX.DE", "MRK.DE", "BEI.DE", "MTX.DE", "DB1.DE",
        "CBK.DE", "DBK.DE", "ADS.DE", "HEI.DE", "CON.DE", "HEN3.DE", "SY1.DE", "VNA.DE", "EON.DE", "RWE.DE",
        "DTG.DE", "MUV2.DE", "ZAL.DE", "HNR1.DE", "QIA.DE", "FRE.DE", "FME.DE", "SHL.DE", "BNR.DE", "KGX.DE",
        "PUM.DE", "WDI.DE", "LEG.DE", "TAG.DE", "FRA.DE", "G1A.DE", "LHA.DE", "EVK.DE", "LAN.DE", "SDF.DE",
        "HLE.DE", "TKWY.DE", "SYAB.DE", "AFX.DE", "HOT.DE", "NDX1.DE", "JEN.DE", "AIXA.DE", "SOW.DE", "EVT.DE",
        "MOR.DE", "BOSS.DE", "BC8.DE", "WAF.DE", "FPE3.DE", "FNTN.DE", "BVB.DE", "TKA.DE", "GXI.DE", "UTDI.DE",
        "1U1.DE", "SMHN.DE", "PBB.DE", "GFT.DE", "O2D.DE", "ADV.DE", "VAR1.DE", "ETL.DE", "LXS.DE", "JUN3.DE",
        "KRN.DE", "GBF.DE", "HDD.DE", "AM3D.DE", "GLJ.DE", "PSM.DE", "NOEJ.DE", "AOX.DE", "HBH.DE", "DUE.DE"
    ]

    # --- US POWER-LISTE (50) ---
    us_list = [
        "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK-B", "LLY", "AVGO",
        "V", "JPM", "MA", "UNH", "HD", "PG", "COST", "NFLX", "ABBV", "ADBE",
        "CRM", "ORCL", "AMD", "BAC", "PEP", "KO", "CVX", "XOM", "TMO", "WMT",
        "DIS", "INTC", "CSCO", "VZ", "PFE", "NKE", "INTU", "QCOM", "TXN", "AMAT",
        "ISRG", "BKNG", "MU", "PANW", "GILD", "LRCX", "SBUX", "PYPL", "SNPS", "CDNS"
    ]

    final_list = list(set(de_list + us_list))
    
    # Ab hier versuchen wir zusätzlich Wikipedia zu laden
    # Ersetze den alten headers-Eintrag durch diesen hier:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7'
    }
    
    # ... der Rest des Codes mit der for-Schleife über die indices folgt hier ...
    indices = {
        "DAX": "Liste_der_im_DAX_gelisteten_Unternehmen",
        "MDAX": "Liste_der_im_MDAX_gelisteten_Unternehmen",
        "SDAX": "Liste_der_im_SDAX_gelisteten_Unternehmen"
    }

    for name, path in indices.items():
        try:
            url = f"https://de.wikipedia.org/wiki/{path}"
            resp = requests.get(url, headers=headers, timeout=15)
            # Nutze StringIO um die Future-Warnung zu vermeiden
            from io import StringIO
            tables = pd.read_html(StringIO(resp.text))
            
            for df in tables:
                # Suche Spalte mit "Symbol" oder "Kürzel"
                col = next((c for c in df.columns if any(x in str(c) for x in ['Symbol', 'Kürzel', 'Ticker'])), None)
                if col:
                    found = df[col].dropna().astype(str).tolist()
                    clean = [f"{s.split(':')[ -1].strip()}.DE" for s in found if len(s) < 10]
                    final_list.extend(clean)
                    print(f"✅ {name}: {len(clean)} Ticker geladen.")
                    break
        except Exception as e:
            print(f"⚠️ Fehler bei {name}: {e}")

    # Duplikate entfernen und leere Einträge filtern
    return list(set([t for t in final_list if t and len(t) > 2]))

# --- 3. SCREENER & RUN ---
def run_sentinel():
    print(f"🚀 Scan Start: {datetime.now()}")
    all_tickers = get_tickers()
    print(f"Gesamt-Pool: {len(all_tickers)} Aktien.")
    
    # Download Markt-Daten
    data = yf.download(all_tickers, period="60d", interval="1d", group_by='ticker', progress=False)
    
    signals = []
    for ticker in all_tickers:
        try:
            df = data[ticker].dropna()
            if len(df) < 30: continue
            
            close = df['Close'].iloc[-1]
            avg_vol = df['Volume'].rolling(20).mean().iloc[-1]
            rel_vol = df['Volume'].iloc[-1] / avg_vol
            sma_50 = df['Close'].rolling(50).mean().iloc[-1]
            
            # Etwas lockerer für den ersten Live-Tag (1.5 statt 1.8)
            if rel_vol > 1.5 and close > sma_50:
                signals.append({'Ticker': ticker, 'Price': round(close, 2), 'Vol': round(rel_vol, 1)})
        except: continue

    # Nachrichten-Versand
    if signals:
        for s in signals:
            try:
                prompt = f"Aktie {s['Ticker']} hat heute {s['Vol']}x normales Volumen. Warum? Suche News 2026. 1 Satz."
                res = model.generate_content(prompt)
                msg = f"🎯 *SIGNAL: {s['Ticker']}*\n💰 Preis: {s['Price']}€\n📊 Vol: {s['Vol']}x\n🤖 KI: {res.text}"
                send_telegram_msg(msg)
            except: pass
    
    # Abschlussbericht
    send_telegram_msg(f"✅ *Sentinel Scan beendet*\n🔢 Geprüft: {len(all_tickers)} Aktien\n🎯 Signale: {len(signals)}")

if __name__ == "__main__":
    run_sentinel()
