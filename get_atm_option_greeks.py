from ib_insync import IB, Stock, Option
import datetime as dt

def main():
    ib = IB()
    ib.connect('127.0.0.1', 7497, clientId=1)  # TWS/PaperTrader kører normalt på port 7497

    # === Brug delayed market data ===
    ib.reqMarketDataType(3)  # 3 = delayed

    ticker = "AAPL"

    # === 1) Hent spotpris ===
    stock = Stock(ticker, "SMART", "USD")
    stock_data = ib.reqMktData(stock, snapshot=True)
    ib.sleep(2)  # vent lidt så data kan komme ind

    if not stock_data.last:
        print(f"⚠️ Ingen spotpris fundet for {ticker}.")
        ib.disconnect()
        return

    spot = float(stock_data.last)
    print(f"✅ Spotpris for {ticker}: {spot}")

    # === 2) Find ATM strike (afrund til nærmeste 5) ===
    atm_strike = round(spot / 5) * 5
    print(f"📌 Valgt ATM strike: {atm_strike}")

    # === 3) Find udløb ~30 dage ude ===
    expiry = (dt.date.today() + dt.timedelta(days=30)).strftime("%Y%m%d")
    print(f"📌 Valgt udløb: {expiry}")

    # === 4) Byg Option kontrakt ===
    option = Option(
        symbol=ticker,
        lastTradeDateOrContractMonth=expiry,
        strike=atm_strike,
        right="C",  # Call
        exchange="SMART",
        currency="USD"
    )

    # === 5) Hent option data inkl. Greeks ===
    opt_data = ib.reqMktData(option, "", False, False)
    ib.sleep(3)

    if opt_data.modelGreeks:
        g = opt_data.modelGreeks
        print(f"""
        📊 Option Data for {ticker} {expiry} {atm_strike}C
        ---------------------------------------------
        Implied Vol: {g.impliedVol*100:.2f}%
        Delta: {g.delta:.4f}
        Gamma: {g.gamma:.4f}
        Vega: {g.vega:.4f}
        Theta: {g.theta:.4f}
        Und. Price: {g.undPrice:.2f}
        Bid: {opt_data.bid}
        Ask: {opt_data.ask}
        Last: {opt_data.last}
        """)
    else:
        print(f"⚠️ Ingen Greeks/IV returneret. Har du delayed option data aktiveret i TWS?")

    ib.disconnect()

if __name__ == "__main__":
    main()
