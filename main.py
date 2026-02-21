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
    model = genai.GenerativeModel('gemini-1.5-flash')

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
    send_telegram_msg("🔔 *Sentinel Systemcheck*\nVerbindung erfolgreich hergestellt!")

    # Test-Ticker
    tickers = ["PNTX.DE", "PZNA.DE", "SZA.DE"]
    
    try:
        # Lade Daten mit längerer Historie, um Wochenend-Lücken zu füllen
        data = yf.download(tickers, period="1mo", interval="1d", progress=False)
        
        if data.empty or 'Close' not in data:
            send_telegram_msg("⚠️ Keine Marktdaten verfügbar (Wochenende).")
            return

        # Sicherer Zugriff auf den letzten verfügbaren Preis
        last_prices = data['Close'].ffill().iloc[-1]
        
        for ticker in tickers:
            if ticker in last_prices:
                price = round(last_prices[ticker], 2)
                # KI-Analyse
                prompt = f"Gib eine 1-Satz-Prognose für die Aktie {ticker} (Preis: {price}€) für das Jahr 2026."
                try:
                    response = model.generate_content(prompt)
                    msg = f"📈 *Update: {ticker}*\nPreis: {price}€\n🤖 AI: {response.text}"
                    send_telegram_msg(msg)
                except:
                    send_telegram_msg(f"📈 *Update: {ticker}*\nPreis: {price}€\n(KI-Dienst momentan überlastet)")
                    
    except Exception as e:
        print(f"Fehler: {e}")
        send_telegram_msg(f"❌ System-Fehler: {str(e)[:50]}")

if __name__ == "__main__":
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("❌ Telegram Konfiguration fehlt!")
    else:
        run_logic()
