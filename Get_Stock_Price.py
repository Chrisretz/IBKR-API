from ib_insync import IB, Stock, Option
import pandas as pd

# === 1) Forbind til TWS eller Gateway ===
ib = IB()
ib.connect('127.0.0.1', 7497, clientId=2)

# === 2) Definer og kvalificer AAPL kontrakten ===
stock = Stock('AAPL', 'SMART', 'USD')
ib.qualifyContracts(stock)

from datetime import datetime

# === 3) Hent spotpris (med fallback) ===
ib.reqMarketDataType(1)  # 1 = real-time streaming
ticker = ib.reqMktData(stock, snapshot=True)
ib.sleep(2)

spot_price = ticker.last or ticker.close

if spot_price:
    print(f"✅ Spotpris (real-time eller delayed) for AAPL: {spot_price}")
else:
    print("⚠️ Ingen real-time/delayed data – henter historisk close...")
    bars = ib.reqHistoricalData(
        stock,
        endDateTime='',
        durationStr='2 D',          # bed om to dage for at være sikker på at få data
        barSizeSetting='1 day',
        whatToShow='TRADES',
        useRTH=True,
        formatDate=1
    )
    if bars and len(bars) > 0:
        spot_price = bars[-1].close
        bar_time = bars[-1].date.strftime('%Y-%m-%d') if isinstance(bars[-1].date, datetime) else bars[-1].date
        print(f"✅ Spotpris (EOD close fra {bar_time}) for AAPL: {spot_price}")
    else:
        print("❌ Kunne ikke hente historiske data – check API eller markedskalender.")
        ib.disconnect()
        exit()


# === 4) Hent option chain ===
chains = ib.reqSecDefOptParams(
    underlyingSymbol='AAPL',
    futFopExchange='',
    underlyingSecType='STK',
    underlyingConId=stock.conId
)

smart_chain = next(c for c in chains if c.exchange == 'SMART')
print(f"🔗 Fundet option chain med {len(smart_chain.strikes)} strikes og {len(smart_chain.expirations)} expirations")

# === 5) Filtrer strikes og expirations ===
strikes = sorted(s for s in smart_chain.strikes if (spot_price - 10) < s < (spot_price + 10))
expirations = sorted(smart_chain.expirations)[:2]

print(f"📊 Henter {len(strikes)} strikes og {len(expirations)} expirations")

if not strikes:
    print("⚠️ Ingen strikes fundet i det valgte interval – tjek om spotpris er korrekt.")
    ib.disconnect()
    exit()

# === 6) Opret option-kontrakter ===
options = []
for expiry in expirations:
    for strike in strikes:
        options.append(Option('AAPL', expiry, strike, 'C', 'SMART'))
        options.append(Option('AAPL', expiry, strike, 'P', 'SMART'))

ib.qualifyContracts(*options)

# === 7) Hent market data for optionerne ===
ib.reqMarketDataType(4)  # 4 = delayed-frozen uden for åbningstid
tickers = []
for opt in options:
    t = ib.reqMktData(opt, snapshot=True)
    tickers.append(t)

ib.sleep(5)  # Vent på at data kommer ind

# === 8) Saml resultater i DataFrame ===
data = []
for opt, ticker in zip(options, tickers):
    data.append({
        "expiry": opt.lastTradeDateOrContractMonth,
        "strike": opt.strike,
        "type": opt.right,
        "last": ticker.last,
        "bid": ticker.bid,
        "ask": ticker.ask,
        "iv": ticker.modelGreeks.impliedVol if ticker.modelGreeks else None,
        "delta": ticker.modelGreeks.delta if ticker.modelGreeks else None,
        "gamma": ticker.modelGreeks.gamma if ticker.modelGreeks else None,
        "vega": ticker.modelGreeks.vega if ticker.modelGreeks else None,
        "theta": ticker.modelGreeks.theta if ticker.modelGreeks else None
    })

df = pd.DataFrame(data)
print(df)

ib.disconnect()
