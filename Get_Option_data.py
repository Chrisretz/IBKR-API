from helpers import connect_ib, disconnect_ib, ib
from ib_insync import Stock, Option
import datetime as dt
import sys

def get_atm_option_iv(ticker: str, exchange: str = "SMART", currency: str = "USD"):
    connect_ib()

    # === 1) Stock contract ===
    stock = Stock(ticker, exchange, currency)
    ib.qualifyContracts(stock)

    mkt_data = ib.reqMktData(stock, snapshot=True)
    ib.sleep(2)

    if not mkt_data.last:
        print(f"⚠️ Ingen aktiekurs fundet for {ticker}.")
        disconnect_ib()
        return
    last_price = float(mkt_data.last)
    print(f"✅ Seneste pris for {ticker}: {last_price}")

    # === 2) Option chain info ===
    chains = ib.reqSecDefOptParams(stock.symbol, '', stock.secType, stock.conId)
    if not chains:
        print(f"⚠️ Ingen option chain fundet for {ticker}.")
        disconnect_ib()
        return

    chain = chains[0]  # typisk SMART chain
    expiries = sorted(chain.expirations)
    strikes = sorted(chain.strikes)

    if not expiries or not strikes:
        print(f"⚠️ Ingen expiries eller strikes fundet for {ticker}.")
        disconnect_ib()
        return

# === 3) Find expiry ca. 30 dage ude ===
target_date = dt.date.today() + dt.timedelta(days=30)
expiry = min(
    expiries,
    key=lambda d: abs(dt.datetime.strptime(d, "%Y%m%d").date() - target_date)
)
print(f"📅 Valgt expiry: {expiry}")

