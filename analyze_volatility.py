from ib_insync import IB, Stock, Option, util
import pandas as pd
import numpy as np
import datetime as dt

# ========= Opret IB-forbindelse =========
ib = IB()

def connect_ib():
    if not ib.isConnected():
        ib.connect('127.0.0.1', 7497, clientId=1)
        ib.reqMarketDataType(3)  # 3 = delayed (brug 1 for real-time hvis du har data)
        print("✅ Forbundet til IBKR.")

def disconnect_ib():
    if ib.isConnected():
        ib.disconnect()
        print("🔌 Forbindelse afbrudt.")

# === Helper: find næste fredag ≥ en given dato ===
def get_next_friday(start_date: dt.date) -> dt.date:
    days_ahead = 4 - start_date.weekday()  # fredag = 4
    if days_ahead < 0:
        days_ahead += 7
    return start_date + dt.timedelta(days=days_ahead)

def get_volatility_with_iv(ticker: str, exchange: str = "SMART", currency: str = "USD"):
    connect_ib()

    # === Hent aktiekontrakt og seneste pris ===
    contract = Stock(ticker, exchange, currency)
    contract = ib.qualifyContracts(contract)[0]

    market_price_data = ib.reqMktData(contract, snapshot=True)
    ib.sleep(2)
    try:
        last_price = float(market_price_data.last)
        print(f"📊 Spotpris for {ticker}: {last_price}")
    except (TypeError, ValueError):
        print(f"⚠️ Kunne ikke hente aktuel pris for {ticker}.")
        disconnect_ib()
        return

    # === Hent 1 års historiske aktiedata (Realized Vol) ===
    bars = ib.reqHistoricalData(
        contract,
        endDateTime='',
        durationStr='1 Y',
        barSizeSetting='1 day',
        whatToShow='TRADES',
        useRTH=True,
        formatDate=1
    )
    df = util.df(bars)
    if df.empty:
        print(f"⚠️ Ingen historiske data hentet for {ticker}.")
        disconnect_ib()
        return

    # Beregn realiseret vol
    df['returns'] = df['close'].pct_change()
    realized_vol = df['returns'].std() * np.sqrt(252)
    print(f"✅ Realiseret volatilitet ({ticker}, 1 år): {realized_vol*100:.2f}%")

    # === Find ATM option, næste fredag ca. 30 dage ude ===
    target_date = dt.date.today() + dt.timedelta(days=30)
    expiry = get_next_friday(target_date).strftime("%Y%m%d")
    atm_strike = round(last_price / 5) * 5  # rund til nærmeste 5 USD strike

    option = Option(
        symbol=ticker,
        lastTradeDateOrContractMonth=expiry,
        strike=atm_strike,
        right='C',  # Call option
        exchange=exchange,
        currency=currency
    )

    # === Hent IV ===
    snapshot = ib.reqMktData(option, snapshot=True)
    ib.sleep(2)

    if snapshot.modelGreeks and snapshot.modelGreeks.impliedVol:
        iv = snapshot.modelGreeks.impliedVol
        print(f"📈 Implied Volatility ({ticker}, ATM {atm_strike}, expiry {expiry}): {iv*100:.2f}%")
    else:
        print(f"⚠️ Ingen IV returneret for {ticker} (expiry {expiry}). "
              f"Tjek om du har det rigtige options data abonnement.")

    disconnect_ib()

if __name__ == "__main__":
    ticker = input("Indtast ticker (fx AAPL, NVDA, NVO): ").strip().upper()
    get_volatility_with_iv(ticker)
