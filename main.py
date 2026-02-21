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
    # Geänderte Modell-Initialisierung für bessere Kompatibilität
    model = genai.GenerativeModel('models/gemini-1.5-flash')

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, json=payload)
        print(f"Telegram Status: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"Telegram Error: {e}")

# --- 2. LOGIK ---
def run_logic():
    print("🚀 Starte Sentinel...")
    
    # Test-Ticker für das Wochenende
    tickers = ["PNTX.DE", "PZNA.DE", "SZA.DE"]
    
    # Nachricht erzwingen (um 401 Fehler zu debuggen)
    send_telegram_msg("🔔 *Sentinel Online*\nPrüfe Markt-Daten...")

    try:
        data = yf.download(tickers, period="5d", interval="1d", progress=False)
        # Wir nehmen einfach den ersten Ticker für einen KI-Test
        ticker = tickers[0]
        close_price = round(data['Close'][ticker].iloc[-1], 2)
        
        prompt = f"Aktie {ticker} steht bei {close_price}€. Gib eine extrem kurze Einschätzung für 2026 (1 Satz)."
        response = model.generate_content(prompt)
        
        final_msg = f"📈 *Update: {ticker}*\nPreis: {close_price}€\n🤖 KI: {response.text}"
        send_telegram_msg(final_msg)
    except Exception as e:
        print(f"Fehler in der Verarbeitung: {e}")
        send_telegram_msg(f"⚠️ Fehler: {str(e)[:100]}")

if __name__ == "__main__":
    if not TELEGRAM_TOKEN or not CHAT_ID or not GEMINI_KEY:
        print("❌ Secrets fehlen in GitHub!")
    else:
        run_logic()
