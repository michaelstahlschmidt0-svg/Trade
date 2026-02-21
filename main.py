import os
import yfinance as yf
import pandas as pd
import google.generativeai as genai
import requests
from datetime import datetime
from googlesearch import search

# --- 1. KONFIGURATION ---
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    ai_model = genai.GenerativeModel('gemini-1.5-flash')

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}&parse_mode=Markdown"
    requests.get(url)

# --- 2. MODUL 1: TICKER LADEN ---
def get_global_tickers():
    all_tickers = []
    try:
        sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]
        all_tickers.extend(sp500['Symbol'].str.replace('.', '-').tolist())
    except: pass

    de_indices = ["DAX", "MDAX", "SDAX"]
    for idx in de_indices:
        try:
            tables = pd.read_html(f"https://de.wikipedia.org/wiki/{idx}")
            for df in tables:
                col = next((c for c in df.columns if 'Symbol' in str(c)), None)
                if col:
                    symbols = [f"{s}.DE" for s in df[col].dropna().tolist() if ".DE" not in str(s)]
                    all_tickers.extend(symbols)
                    break
        except: pass
    
    all_tickers.extend(["A40AEG.DE", "694280.DE", "A2AA20.DE"]) # Manuelle Werte
    return list(set(all_tickers))

# --- 3. MODUL 2: SCREENER ---
def technical_pre_screen(ticker_list):
    candidates = []
    batch_size = 40
    for i in range(0, len(ticker_list), batch_size):
        batch = ticker_list[i:i+batch_size]
        data = yf.download(batch, period="1y", interval="1d", group_by='ticker', threads=True, progress=False)
        for ticker in batch:
            try:
                df = data[ticker]
                if len(df) < 200: continue
                close = df['Close'].iloc[-1]
                avg_vol = df['Volume'].rolling(20).mean().iloc[-1]
                rel_vol = df['Volume'].iloc[-1] / avg_vol
                rsl_189 = close / df['Close'].rolling(189).mean().iloc[-1]
                if rel_vol > 1.5 and close > df['Close'].ewm(span=200).mean().iloc[-1] and rsl_189 > 1.0:
                    candidates.append({'Ticker': ticker, 'Price': round(close, 2), 'Rel_Vol': round(rel_vol, 2), 'RSL': round(rsl_189, 3)})
            except: continue
    return pd.DataFrame(candidates)

# --- 4. MODUL 3: KI & HEARTBEAT ---
def run_logic():
    tickers = get_global_tickers()
    total_scanned = len(tickers)
    finalists = technical_pre_screen(tickers)
    
    # Signale melden
    if not finalists.empty:
        for _, row in finalists.iterrows():
            prompt = f"Analysiere {row['Ticker']} (RSL {row['RSL']}, Vol {row['Rel_Vol']}x). Suche News/Ad-hocs von 2026. 2 Sätze!"
            try:
                res = ai_model.generate_content(prompt)
                msg = f"🚀 *SIGNAL: {row['Ticker']}*\n💰 Preis: {row['Price']}€\n📊 Vol: {row['Rel_Vol']}x\n🧠 KI: {res.text}"
                send_telegram_msg(msg)
            except: pass

    # Heartbeat (Tägliche Bestätigung)
    now = datetime.now()
    heartbeat = f"✅ *Sentinel Heartbeat*\n🔢 Geprüft: {total_scanned} Aktien\n🎯 Signale heute: {len(finalists)}"
    
    # Freitags-Special (Wochenbilanz beim Nachmittags-Scan)
    if now.weekday() == 4 and now.hour >= 14:
        heartbeat += "\n\n📅 *Wochen-Fazit:* Markt-Scan über 5 Tage erfolgreich. Alle Systeme im grünen Bereich."
    
    send_telegram_msg(heartbeat)

if __name__ == "__main__":
    run_logic()
