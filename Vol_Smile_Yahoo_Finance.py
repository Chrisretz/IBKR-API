import yfinance as yf
import matplotlib.pyplot as plt
import numpy as np

# Vælg ticker
ticker = yf.Ticker("AAPL")

# Hent spotkurs (seneste lukkekurs)
spot_price = ticker.history(period="1d")["Close"].iloc[-1]

# Vælg en udløbsdato (her den første tilgængelige)
expiry = ticker.options[0]
opt_chain = ticker.option_chain(expiry)

calls = opt_chain.calls.copy()
puts = opt_chain.puts.copy()

# ========== BEREGN ATM-IV OG RANGE ==========
# Find strike tættest på spot (ATM)
atm_strike_idx = (calls['strike'] - spot_price).abs().idxmin()
atm_iv = calls.loc[atm_strike_idx, 'impliedVolatility']

# Tid til udløb i år (her ca. 30 dage som eksempel)
T = 30 / 365  
sigma_exp = atm_iv * np.sqrt(T)

# Sæt filtergrænser (±2σ)
lower = spot_price * (1 - 2 * sigma_exp)
upper = spot_price * (1 + 2 * sigma_exp)

# Filtrér strikes (indenfor range + kræv openInterest > 0)
calls_filtered = calls[(calls['strike'] >= lower) & (calls['strike'] <= upper) & (calls['openInterest'] > 0)]
puts_filtered = puts[(puts['strike'] >= lower) & (puts['strike'] <= upper) & (puts['openInterest'] > 0)]

# ========== PLOT ==========
plt.figure(figsize=(10,6))

plt.plot(calls_filtered["strike"], calls_filtered["impliedVolatility"], label="Calls", marker="o")
plt.plot(puts_filtered["strike"], puts_filtered["impliedVolatility"], label="Puts", marker="x")

# Lodret linje ved spot
plt.axvline(x=spot_price, color="red", linestyle="--", linewidth=1.5, label=f"Spot ({spot_price:.2f})")

plt.title(f"Volatility Smile for AAPL ({expiry}) – filtreret ±2σ og OI>0")
plt.xlabel("Strike")
plt.ylabel("Implied Volatility")
plt.legend()
plt.grid(True)
plt.show()
