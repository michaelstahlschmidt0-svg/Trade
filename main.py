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
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}&parse_mode=Markdown"
    requests.get(url)

# --- 2. MODUL 1: TICKER LADEN ---
def get_global_tickers():
    all_tickers = [] # Hier wird die Liste sauber definiert
    
    # USA: S&P 500
    try:
        sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]
        all_tickers.extend(sp500['Symbol'].str.replace('.', '-').tolist())
    except: 
        print("⚠️ Fehler beim Laden des S&P 500")

    # DE: DAX, MDAX, SDAX
    de_indices = ["DAX", "MDAX", "SDAX"]
    for idx in de_indices:
        try:
            tables = pd.read_html(f"https://de.wikipedia.org/wiki/Liste_der_im_{idx}_gelisteten_Unternehmen")
            for df in tables:
                col = next((c for c in df.columns if 'Symbol' in str(c) or 'Kürzel' in str(c)), None)
                if col:
                    symbols = [f"{s}.DE" for s in df[col].dropna().tolist() if ".DE" not in str(s)]
                    all_tickers.extend(symbols)
                    break
        except: 
            print(f"⚠️ Fehler beim Laden von {idx}")
    
    # Korrekte Yahoo-Kürzel für deine Favoriten
    # PNTX.DE = Pentixapharm, PZNA.DE = Scherzer, SZA.DE = Scherzer & Co.
    all_tickers.extend(["PNTX.DE", "PZNA.DE", "SZA.DE"]) 
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
                if len(df) < 150: continue # Etwas lockerer für Nebenwerte
                close = df['Close'].iloc[-1]
                avg_vol = df['Volume'].rolling(20).mean().iloc[-1]
                rel_vol = df['Volume'].iloc[-1] / avg_vol
                rsl_189 = close / df['Close'].rolling(150).mean().iloc[-1]
                
                # Filter-Logik
                if rel_vol > 1.2 and close > df['Close'].ewm(span=200).mean().iloc[-1]:
                    candidates.append({
                        'Ticker': ticker, 
                        'Price': round(close, 2), 
                        'Rel_Vol': round(rel_vol, 2), 
                        'RSL': round(rsl_189, 3)
                    })
            except: continue
    return pd.DataFrame(candidates)

# --- 4. MODUL 3: KI & NOTIFICATION ---
def run_ai_and_notify(df, total_scanned):
    hits = len(df)
    if hits > 0:
        for _, row in df.iterrows():
            ticker = row['Ticker']
            prompt = f"Analysiere Aktie {ticker}. Technische Stärke: RSL {row['RSL']}, Vol {row['Rel_Vol']}x. Suche News (Rückkauf, Zulassung). 2 Sätze!"
            try:
                res = ai_model.generate_content(prompt)
                msg = f"🚀 *SIGNAL: {ticker}*\n💰 Preis: {row['Price']}€\n📊 Vol: {row['Rel_Vol']}x\n🧠 KI: {res.text}"
                send_telegram_msg(msg)
            except: pass

    # Heartbeat
    now = datetime.now()
    heartbeat = f"✅ *Sentinel Heartbeat*\n🔢 Geprüft: {total_scanned} Aktien\n🎯 Signale heute: {hits}"
    if now.weekday() == 5 or now.weekday() == 6:
        heartbeat += "\n\n🏝️ *Wochenende:* Markt-Daten sind statisch."
    send_telegram_msg(heartbeat)

# --- 5. STARTPUNKT ---
if __name__ == "__main__":
    if not TELEGRAM_TOKEN or not CHAT_ID or not GEMINI_KEY:
        print("❌ Fehler: Secrets fehlen!")
    else:
        tickers = get_global_tickers()
        finalists = technical_pre_screen(tickers)
        
        # Falls Wochenende/Keine Signale: Test mit Pentixapharm erzwingen
        if finalists.empty:
            print("Keine Signale. Sende Test-Check...")
            test_data = pd.DataFrame([{'Ticker': 'PNTX.DE', 'Price': 5.10, 'Rel_Vol': 2.1, 'RSL': 1.15}])
            run_ai_and_notify(test_data, len(tickers))
        else:
            run_ai_and_notify(finalists, len(tickers))
