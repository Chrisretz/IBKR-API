from ib_insync import IB, Stock
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# === INPUT VARIABLER ===
TICKER = "INTC"   # <- skriv din ønskede ticker her (f.eks. "MSFT", "TSLA")
YEARS = 3         # <- antal års historik (f.eks. 1, 2, 5)

# === CONNECT ===
ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)
print("Connected:", ib.isConnected())

ib.reqMarketDataType(3)  # Brug delayed data (3 = delayed)
contract = Stock(TICKER, 'SMART', 'USD')
durationStr = f"{YEARS} Y"

# Hent historiske priser
price_bars = ib.reqHistoricalData(
    contract, '', durationStr, '1 day', 'TRADES', useRTH=True, formatDate=1
)

# Hent implied volatility
iv_bars = ib.reqHistoricalData(
    contract, '', durationStr, '1 day', 'OPTION_IMPLIED_VOLATILITY', useRTH=True, formatDate=1
)

# Konverter til DataFrames
df_price = pd.DataFrame(price_bars)
df_iv = pd.DataFrame(iv_bars)
df_price['date'] = pd.to_datetime(df_price['date'])
df_iv['date'] = pd.to_datetime(df_iv['date'])
df_price.set_index('date', inplace=True)
df_iv.set_index('date', inplace=True)

# Merge
df = df_price[['close']].rename(columns={'close': 'price'}).merge(
    df_iv[['close']].rename(columns={'close': 'iv'}),
    left_index=True, right_index=True, how='inner'
)

# === REALIZED VOLATILITY ===
df['returns'] = np.log(df['price'] / df['price'].shift(1))
df['rv_30d'] = df['returns'].rolling(window=30).std() * np.sqrt(252)

# Beregn gennemsnit
mean_iv = df['iv'].mean()
mean_rv = df['rv_30d'].mean()

# Beregn spread
df['iv_rv_spread'] = df['iv'] - df['rv_30d']

# === PLOT ===
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16,6))

# --- VENSTRE PLOT ---
ax1a = ax1
ax1b = ax1a.twinx()

# Price
ax1a.plot(df.index, df['price'], color='blue', label=f'{TICKER} Price')
ax1a.set_xlabel('Date')
ax1a.set_ylabel('Price (USD)', color='blue')
ax1a.tick_params(axis='y', labelcolor='blue')

# IV og RV
ax1b.plot(df.index, df['iv'], color='red', label='Implied Volatility')
ax1b.plot(df.index, df['rv_30d'], color='green', linestyle='--', label='30D Realized Volatility')
ax1b.axhline(mean_iv, color='red', linestyle=':', alpha=0.7, label=f'Mean IV ({mean_iv:.2%})')
ax1b.axhline(mean_rv, color='green', linestyle=':', alpha=0.7, label=f'Mean RV ({mean_rv:.2%})')

ax1b.set_ylabel('Volatility (annualized)', color='red')
ax1b.tick_params(axis='y', labelcolor='red')

# Legende
lines1, labels1 = ax1a.get_legend_handles_labels()
lines2, labels2 = ax1b.get_legend_handles_labels()
ax1b.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

ax1a.set_title(f'{TICKER}: Price, IV & RV')

# --- HØJRE PLOT ---
mean_spread = df['iv_rv_spread'].mean()

ax2.plot(df.index, df['iv_rv_spread'], color='purple', label='IV - RV Spread')
ax2.axhline(0, color='black', linestyle='--', alpha=0.7, label='Zero Line')
ax2.axhline(mean_spread, color='orange', linestyle=':', alpha=0.9,
            label=f'Mean Spread ({mean_spread:.2%})')

ax2.set_xlabel('Date')
ax2.set_ylabel('IV - RV Spread')
ax2.legend(loc='upper left')
ax2.set_title(f'{TICKER}: IV - RV Spread')


plt.tight_layout()
plt.show()

ib.disconnect()
