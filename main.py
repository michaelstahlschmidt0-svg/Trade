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
        "UTDI.DE", "1U1.DE", "SMHN.DE", "PBB.DE", "GFT.DE", "O2D.HM", "ETS.VI", "LXS.DE", 
        "JUN3.DE", "KRN.DE", "GBF.DE", "HDD.DE", "GLJ.DE", "PSM.DE", "NOEJ.DE", 
        
    ]
    us_list = [
        "WYNN", "XEL", "XYL", "YUM", "ZBRA", "ZBH", "ZTS", "ZS", "ASML", 
        "WAT", "WFC", "WELL", "WST", "WDC", "WY", "WMB", "WSM", "WDAY", 
        "VICI", "V", "VST", "VMC", "WEC", "WAB", "WMT", "WBD", "WM", 
        "UHS", "VLO", "VTR", "VLTO", "VRSN", "VZ", "VRSK", "VRTX", "VTRS", 
        "UDR", "USB", "UBER", "ULTA", "UNP", "UAL", "UPS", "URI", "UNH", 
        "TMO", "MMM", "TSCO", "TDG", "TRV", "TRMB", "TFC", "TYL", "TSN", 
        "TGT", "TRGP", "TDY", "TER", "TSLA", "TXN", "TPL", "TXT", "TTD", 
        "SMCI", "SNPS", "SYF", "SYY", "TJX", "TKO", "TMUS", "TTWO", "TPR", 
        "SOLV", "SO", "LUV", "XYZ", "SWK", "SBUX", "STT", "STLD", "SYK", 
        "SCHW", "SRE", "NOW", "SHW", "SPG", "SWKS", "AOS", "SJM", "SNA", 
        "RMD", "ROK", "ROL", "ROP", "ROST", "SPGI", "SBAC", "CRM", "HSIC", 
        "DGX", "RL", "OKU1.L", "RTX", "O", "REG", "REGN", "RF", "RSG", 
        "PG", "PGR", "PLD", "PRU", "PEG", "PSA", "PHM", "QCOM", "PWR", 
        "PKN.SG", "PFE", "PM", "PSX", "OA2S.L", "PNW", "POOL", "TROW", "PFG", 
        "PCAR", "PKG", "PLTR", "PANW", "PH", "PAYX", "PAYC", "PYPL", "PEP", 
        "ON", "OKE", "ORCL", "OTIS", "PCG", "PNC", "PPG", "PPL", "PTC", 
        "NTRS", "NOC", "GEN", "NUE", "NVDA", "ORLY", "OXY", "ODFL", "OMC", 
        "NFLX", "NEM", "NWS", "NWSA", "NEE", "NKE", "NI", "NDSN", "NSC", 
        "MNST", "MCO", "MS", "MOS", "MSI", "NRG", "NVR", "NDAQ", "NTAP", 
        "MU", "MAA", "MRP", "MRNA", "MHK", "MOH", "TAP", "MDLZ", "MPWR", 
        "MCD", "MCK", "MELI", "MRK", "MET", "MTD", "MSFT", "MSTR", "MCHP", 
        "MKTX", "MMC", "MAR", "MLM", "MRVL", "MAS", "MA", "MTCH", "MKC", 
        "LYV", "LMT", "L", "LOW", "LULU", "MTB", "MGM", "MSCI", "MPC", 
        "LH", "LRCX", "LW", "LVS", "EL", "LDOS", "LEN", "LII", "LLY", 
        "KEY", "KEYS", "KMB", "KIM", "KMI", "KHC", "KR", "LKQ", "LHX", 
        "JPM", "JBL", "J", "JNJ", "KLAC", "KKR", "K", "KVUE", "KDP", 
        "ICE", "IBM", "IFF", "IP", "INTU", "ISRG", "INVH", "IQV", "IRM", 
        "HII", "IEX", "IDXX", "ITW", "INCY", "IR", "PODD", "INTC", "IBKR", 
        "HD", "HON", "HRL", "HST", "HWM", "HUBB", "HUM", "JBHT", "HBAN", 
        "HAL", "HIG", "HAS", "DOC", "JKHY", "HSY", "HPE", "HLT", "HO1.F", 
        "GPC", "GILD", "GPN", "GL", "GDDY", "GS", "GWW", "HCA", "HPQ", 
        "GEHC", "AJG", "IT", "GEV", "GNRC", "GD", "GE", "GIS", "GM", 
        "FISV", "FE", "F", "FTNT", "FTV", "FOXA", "FOX", "BEN", "FCX", 
        "FDS", "FICO", "FAST", "FRT", "FDX", "FFIV", "FIS", "FITB", "FSLR", 
        "ESS", "EVRG", "ES", "EXC", "EXPE", "EXPD", "EXR", "XOM", "META", 
        "EA", "EMR", "ENPH", "ETR", "EPAM", "EFX", "EQIX", "EQR", "ERIE", 
        "DUK", "DD", "EOG", "EQT", "EMN", "EBAY", "ECL", "EIX", "EW", 
        "DLR", "DIS", "DG", "DLTR", "D", "DPZ", "DASH", "DOV", "DOW", 
        "DDOG", "DVA", "DECK", "DE", "DELL", "DAL", "DVN", "DXCM", "FANG", 
        "COST", "CSGP", "CRWD", "CCI", "CMI", "DHI", "DTE", "DHR", "DRI", 
        "COP", "ED", "STZ", "CEG", "COO", "CPRT", "GLW", "CPAY", "CTVA", 
        "C", "CFG", "CLX", "KO", "CTSH", "COIN", "CL", "CMCSA", "CAG", 
        "CRL", "CHTR", "EXE", "CVX", "CMG", "CHD", "CINF", "CSCO", "CTAS", 
        "CPT", "CPB", "COF", "CAH", "KMX", "CARR", "CAT", "CNC", "CNP", 
        "CHRW", "CI", "CME", "CMS", "CSX", "CVS", "CTRA", "CDNS", "CZR", 
        "BR", "AVGO", "BRO", "BF-B", "BLDR", "CBOE", "CBRE", "CDW", "CF", 
        "BIIB", "TECH", "BX", "BLK", "BA", "BKNG", "BXP", "BSX", "BMY", 
        "BKR", "BALL", "BAC", "BK", "BAX", "BDX", "WRB", "BRK-B", "BBY", 
        "AZN", "TEAM", "ATO", "ADSK", "ADP", "AZO", "AVB", "AVY", "AXON", 
        "APA", "APO", "AAPL", "AMAT", "APP", "ADM", "ANET", "ARM", "AIZ", 
        "AMT", "AWK", "COR", "AMP", "AME", "AMGN", "APH", "ADI", "ELV", 
        "ALL", "GOOG", "GOOG", "MO", "AMZN", "AEE", "AEP", "AXP", "AIG", 
        "AMD", "A", "ABNB", "APD", "AKAM", "ALB", "ARE", "ALGN", "LNT", 
        "AFL", "AES", "T", "ABT", "ABBV", "ADBE"
        
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
