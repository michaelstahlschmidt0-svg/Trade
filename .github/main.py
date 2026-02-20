import os
import yfinance as yf
import pandas as pd
import google.generativeai as genai
import requests
from googlesearch import search
from tqdm import tqdm

# --- 1. SICHERHEITS-KONFIGURATION (GitHub Secrets) ---
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# KI-Modell initialisieren
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')

# --- 2. MODUL 1: TICKER LADEN ---
def get_global_tickers():
    print("🚀 Lade Ticker-Listen (USA & DE)...")
    all_tickers = []
    
    # USA: S&P 500
    try:
        sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]
        all_tickers.extend(sp500['Symbol'].str.replace('.', '-').tolist())
    except: print("⚠️ Fehler bei S&P 500")

    # DE: DAX, MDAX, SDAX & Scale
    de_indices = ["DAX", "MDAX", "SDAX"]
    for idx in de_indices:
        try:
            url = f"https://de.wikipedia.org/wiki/{idx}"
            tables = pd.read_html(url)
            for df in tables:
                col = next((c for c in df.columns if 'Symbol' in str(c)), None)
                if col:
                    symbols = [f"{s}.DE" for s in df[col].dropna().tolist() if ".DE" not in str(s)]
                    all_tickers.extend(symbols)
                    break
        except: print(f"⚠️ Fehler bei {idx}")
    
    # Manuelle Perlen hinzufügen (z.B. Pentixapharm, Scherzer)
    all_tickers.extend(["A40AEG.DE", "694280.DE", "A2AA20.DE"])
    return list(set(all_tickers))

# --- 3. MODUL 2: TECHNISCHER SCREENER ---
def technical_pre_screen(ticker_list):
    print(f"🔍 Screening von {len(ticker_list)} Titeln...")
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
                ema_200 = df['Close'].ewm(span=200).mean().iloc[-1]

                # DEINE STRATEGIE-FILTER:
                if rel_vol > 1.5 and close > ema_200 and rsl_189 > 1.0:
                    candidates.append({'Ticker': ticker, 'Price': round(close, 2), 'Rel_Vol': round(rel_vol, 2), 'RSL': round(rsl_189, 3)})
            except: continue
            
    return pd.DataFrame(candidates)

# --- 4. MODUL 3: KI-ANALYSE & TELEGRAM ---
def run_ai_and_notify(df):
    for _, row in df.iterrows():
        ticker = row['Ticker']
        prompt = f"Analysiere Aktie {ticker} am 21.02.2026. Technische Stärke: RSL {row['RSL']}, Vol {row['Rel_Vol']}x. Suche Ad-hoc News (Rückkauf, Zulassung, Daten). Antworte in 2 Sätzen: Warum steigt sie? Bewertung?"
        
        try:
            response = model.generate_content(prompt)
            ai_text = response.text
            
            msg = f"🚀 *SIGNAL: {ticker}*\n💰 Preis: {row['Price']}€\n📊 Vol: {row['Rel_Vol']}x\n🧠 KI: {ai_text}"
            
            # Telegram absenden
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown"
            requests.get(url)
            print(f"✅ Alert gesendet für {ticker}")
        except: print(f"⚠️ Fehler bei Analyse {ticker}")

# --- 5. STARTPUNKT ---
if __name__ == "__main__":
    if not TELEGRAM_TOKEN or not CHAT_ID or not GEMINI_KEY:
        print("❌ Fehler: Secrets nicht gefunden!")
    else:
        tickers = get_global_tickers()
        finalists = technical_pre_screen(tickers)
        if not finalists.empty:
            run_ai_and_notify(finalists)
        else:
            print("😴 Heute keine Treffer.")