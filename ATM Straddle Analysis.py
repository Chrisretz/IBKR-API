from ib_insync import IB, Stock, Option
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime as dt

# ========= INPUT =========
TICKER = "AAPL"
USE_DELAYED = True   # True = delayed (3), False = real-time (1)

# ========= CONNECT =========
ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)
print("Connected:", ib.isConnected())
ib.reqMarketDataType(3 if USE_DELAYED else 1)

# ========= 1) UNDERLYING =========
stock = Stock(TICKER, "SMART", "USD")
stock = ib.qualifyContracts(stock)[0]

tick_under = ib.reqMktData(stock, snapshot=True)
ib.sleep(2)
spot = float(tick_under.last) if tick_under.last else None
if spot is None:
    raise ValueError(f"Kunne ikke hente spotpris for {TICKER}")
print(f"Spotpris for {TICKER}: {spot:.2f}")

# ========= 2) OPTION CHAIN & EXPIRY VALG =========
chains = ib.reqSecDefOptParams(stock.symbol, "", stock.secType, stock.conId)
# Brug SMART hvis muligt
chain = next((c for c in chains if c.exchange == "SMART"), chains[0])
all_exchanges = [chain.exchange] + [c.exchange for c in chains if c.exchange != chain.exchange]

expirations = sorted(chain.expirations)
today = dt.date.today()

print("\nTilgængelige expirations:")
for idx, exp in enumerate(expirations, start=1):
    exp_date = dt.datetime.strptime(exp, "%Y%m%d").date()
    days_out = (exp_date - today).days
    print(f"{idx}: {exp} ({days_out} dage til udløb)")

while True:
    try:
        choice = int(input("\nVælg expiry (skriv nummer fra listen): "))
        if 1 <= choice <= len(expirations):
            expiry = expirations[choice - 1]
            break
        else:
            print(f"Ugyldigt valg - vælg et tal mellem 1 og {len(expirations)}.")
    except ValueError:
        print("Skriv venligst et gyldigt tal.")
print(f"\nValgt expiry: {expiry}")

# ========= 3) HENT STRIKES FOR VALGT EXPIRY (uden Error 200 spam) =========
def strikes_for_expiry(symbol: str, expiry_yyyymmdd: str, exchanges: list[str]):
    """
    Returner (exchange, sorted_strikes) for første børs med data for expiry.
    Vi bruger strike=0.0 og right='C'/'P' for at få hele kæden i ét kald.
    """
    for ex in exchanges:
        calls = ib.reqContractDetails(Option(symbol, expiry_yyyymmdd, 0.0, "C", ex))
        puts  = ib.reqContractDetails(Option(symbol, expiry_yyyymmdd, 0.0, "P", ex))
        strikes = sorted({cd.contract.strike for cd in (calls + puts)
                          if cd.contract.strike and cd.contract.strike > 0})
        if strikes:
            return ex, strikes
    return None, []

exch, expiry_strikes = strikes_for_expiry(TICKER, expiry, all_exchanges)
if not expiry_strikes:
    raise ValueError(f"Ingen strikes fundet for {TICKER} {expiry} på nogen exchange ({', '.join(all_exchanges)})")
print(f"Bruger exchange: {exch}")

# Vælg ATM strike blandt reelle strikes
atm_strike = min(expiry_strikes, key=lambda s: abs(s - spot))
print(f"Valgt ATM strike (for {expiry}): {atm_strike}")

# ========= 4) HENT GREEKS & IV FOR ATM CALL/PUT =========
atm_call = Option(TICKER, expiry, atm_strike, "C", exch)
atm_put  = Option(TICKER, expiry, atm_strike, "P", exch)

tick_call = ib.reqMktData(atm_call, "", False, False)
tick_put  = ib.reqMktData(atm_put,  "", False, False)
ib.sleep(3)

gc = tick_call.modelGreeks
gp = tick_put.modelGreeks
if not gc or not gp:
    raise ValueError("Kunne ikke hente Greeks – tjek market data abonnement.")

call_price = tick_call.last if tick_call.last else gc.optPrice
put_price  = tick_put.last  if tick_put.last  else gp.optPrice

# ========= 5) TABELLEN =========
df_opts = pd.DataFrame([
    {"Type": "CALL", "Underlying": TICKER, "Spot": spot, "Expiry": expiry,
     "Strike": atm_strike, "Delta": gc.delta, "Gamma": gc.gamma, "Vega": gc.vega,
     "Theta": gc.theta, "ImpliedVol": gc.impliedVol, "OptPrice": call_price},
    {"Type": "PUT", "Underlying": TICKER, "Spot": spot, "Expiry": expiry,
     "Strike": atm_strike, "Delta": gp.delta, "Gamma": gp.gamma, "Vega": gp.vega,
     "Theta": gp.theta, "ImpliedVol": gp.impliedVol, "OptPrice": put_price}
])
print("\n=== ATM Call & Put (Greeks + IV) ===")
print(df_opts)

# ========= 6) STRADDLE-METRICS =========
straddle_price = call_price + put_price
straddle_pct   = straddle_price / spot
breakeven_up   = spot + straddle_price
breakeven_dn   = spot - straddle_price

expiry_date    = dt.datetime.strptime(expiry, "%Y%m%d").date()
days_to_expiry = max((expiry_date - today).days, 1)

# Vega-vægtet kombineret IV
combined_iv = (
    (gc.impliedVol * gc.vega + gp.impliedVol * gp.vega) / (gc.vega + gp.vega)
    if (gc.vega + gp.vega) != 0 else (gc.impliedVol + gp.impliedVol) / 2
)
annualized_move = straddle_pct / (days_to_expiry ** 0.5) * (252 ** 0.5)
daily_move_pct  = straddle_pct / (days_to_expiry ** 0.5)
daily_move_usd  = daily_move_pct * spot

summary = pd.DataFrame([{
    "Underlying": TICKER,
    "Expiry": expiry,
    "DaysToExpiry": days_to_expiry,
    "Strike(ATM)": atm_strike,
    "Spot": round(spot, 4),
    "StraddlePrice": round(straddle_price, 4),
    "StraddlePctOfSpot": round(straddle_pct, 4),
    "Breakeven_Down": round(breakeven_dn, 4),
    "Breakeven_Up": round(breakeven_up, 4),
    "CombinedIV_VegaWeighted": round(combined_iv, 6),
    "AnnualizedImpliedMove": round(annualized_move, 4),
    "ImpliedDailyMovePct": round(daily_move_pct, 4),
    "ImpliedDailyMoveUSD": round(daily_move_usd, 4)
}])
print("\n=== ATM Straddle Summary ===")
print(summary)

# ========= 7) P&L PLOT =========
price_range = np.linspace(spot * 0.85, spot * 1.15, 200)
call_payoff = np.maximum(price_range - atm_strike, 0)
put_payoff  = np.maximum(atm_strike - price_range, 0)
straddle_pnl = call_payoff + put_payoff - straddle_price

plt.figure(figsize=(10,6))
plt.plot(price_range, straddle_pnl, label='Straddle P&L')
plt.axvline(breakeven_dn, color='red', linestyle='--', label=f'Breakeven Down ({breakeven_dn:.2f})')
plt.axvline(breakeven_up, color='red', linestyle='--', label=f'Breakeven Up ({breakeven_up:.2f})')
plt.axvline(atm_strike, color='black', linestyle=':', label=f'Strike ({atm_strike})')
plt.axvline(spot, color='blue', linestyle=':', alpha=0.7, label=f'Spot ({spot:.2f})')
plt.title(f'{TICKER} ATM Straddle P&L (Expiry {expiry})')
plt.xlabel('Stock Price at Expiry')
plt.ylabel('P&L (USD)')
plt.legend(loc='best')
plt.grid(alpha=0.3)
plt.tight_layout()
plt.show()

ib.disconnect()
