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
    ai_model = genai.GenerativeModel('gemini-1.5-flash')

def send_telegram_msg(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
        r = requests.post(url, data=data)
        print(f"Telegram Response: {r.status_code}")
    except Exception as e:
        print(f"Telegram Fehler: {e}")

# --- 2. MODUL 1: TICKER LADEN ---
def get_global_tickers():
    all_tickers = ["PNTX.DE", "PZNA.DE", "SZA.DE", "SAP.DE", "DTE.DE", "AIR.DE"] 
    # Wikipedia-Scraper mit User-Agent (verhindert 403/404 Fehler)
    headers = {'User-Agent': 'Mozilla/5.0'}
    de_indices = ["DAX", "MDAX", "SDAX"]
    
    for idx in de_indices:
        try:
            url = f"https://de.wikipedia.org/wiki/Liste_der_im_{idx}_gelisteten_Unternehmen"
            html = requests.get(url, headers=headers).text
            tables = pd.read_html(html)
            for df in tables:
                col = next((c for c in df.columns if 'Symbol' in str(c) or 'Kürzel' in str(c)), None)
                if col:
                    symbols = [f"{s}.DE" for s in df[col].dropna().tolist() if ".DE" not in str(s)]
                    all_tickers.extend(symbols)
                    break
        except Exception as e:
            print(f"⚠️ Wiki-Fehler bei {idx}: {e}")
            
    return list(set(all_tickers))

# --- 3. MODUL 2: SCREENER ---
def technical_pre_screen(ticker_list):
    candidates = []
    # Am Wochenende/Test: Nur kleine Auswahl prüfen
    test_batch = ticker_list[:20] 
    data = yf.download(test_batch, period="1mo", interval="1d", progress=False)
    
    for ticker in test_batch:
        try:
            # Check ob Daten da sind
            if ticker not in data['Close']: continue
            close = data['Close'][ticker].iloc[-1]
            if pd.isna(close): continue
            candidates.append({'Ticker': ticker, 'Price': round(close, 2), 'Rel_Vol': 1.0, 'RSL': 1.0})
        except: continue
    return pd.DataFrame(candidates)

# --- 4. MODUL 3: KI & HEARTBEAT ---
def run_logic():
    print("🚀 Starte Logik...")
    tickers = get_global_tickers()
    finalists = technical_pre_screen(tickers)
    
    # TEST-MELDUNG IMMER SENDEN (Um Verbindung zu prüfen)
    test_msg = f"🔔 *Sentinel Test-Check*\nDatum: {datetime.now().strftime('%d.%m.%Y %H:%M')}\nTicker im Pool: {len(tickers)}\n\nStatus: Verbindung steht! 🚀"
    send_telegram_msg(test_msg)

    if not finalists.empty:
        # Nur den ersten Treffer analysieren als Test
        top = finalists.iloc[0]
        prompt = f"Analysiere kurz Aktie {top['Ticker']}. 1 Satz Zukunftsaussicht 2026."
        try:
            res = ai_model.generate_content(prompt)
            msg = f"📈 *Markt-Update: {top['Ticker']}*\nPreis: {top['Price']}€\nAI: {res.text}"
            send_telegram_msg(msg)
        except Exception as e:
            print(f"AI Fehler: {e}")

if __name__ == "__main__":
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("❌ Telegram Secrets fehlen!")
    else:
        run_logic()
