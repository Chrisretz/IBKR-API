from ib_insync import IB, Stock
import pandas as pd
import matplotlib.pyplot as plt

# === INPUT VARIABLER ===
TICKER = "NVDA"   # <- skriv din ønskede ticker her (f.eks. "MSFT", "TSLA")
YEARS = 1         # <- antal års historik (f.eks. 1, 2, 5)

# === CONNECT ===
ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)
print("Connected:", ib.isConnected())

# Brug delayed data (3 = delayed)
ib.reqMarketDataType(3)

# Definer aktien
contract = Stock(TICKER, 'SMART', 'USD')

# Duration string (f.eks. '5 Y')
durationStr = f"{YEARS} Y"

# Hent historiske priser
price_bars = ib.reqHistoricalData(
    contract,
    endDateTime='',
    durationStr=durationStr,
    barSizeSetting='1 day',
    whatToShow='TRADES',
    useRTH=True,
    formatDate=1
)

# Hent implied volatility
iv_bars = ib.reqHistoricalData(
    contract,
    endDateTime='',
    durationStr=durationStr,
    barSizeSetting='1 day',
    whatToShow='OPTION_IMPLIED_VOLATILITY',
    useRTH=True,
    formatDate=1
)

# Konverter til DataFrames
df_price = pd.DataFrame(price_bars)
df_iv = pd.DataFrame(iv_bars)

# Lav datetime index
df_price['date'] = pd.to_datetime(df_price['date'])
df_price.set_index('date', inplace=True)

df_iv['date'] = pd.to_datetime(df_iv['date'])
df_iv.set_index('date', inplace=True)

# Merge
df = df_price[['close']].rename(columns={'close': 'price'}).merge(
    df_iv[['close']].rename(columns={'close': 'iv'}),
    left_index=True, right_index=True, how='inner'
)

print(df.head())

# === PLOT ===
fig, ax1 = plt.subplots(figsize=(12,6))

# Plot aktiekurs
ax1.plot(df.index, df['price'], color='blue', label=f'{TICKER} Price')
ax1.set_xlabel('Date')
ax1.set_ylabel('Price (USD)', color='blue')
ax1.tick_params(axis='y', labelcolor='blue')

# Plot IV på højre y-akse
ax2 = ax1.twinx()
ax2.plot(df.index, df['iv'], color='red', label='Implied Volatility')
ax2.set_ylabel('IV (annualized)', color='red')
ax2.tick_params(axis='y', labelcolor='red')

plt.title(f'{TICKER} Price vs Implied Volatility ({YEARS}Y, Daily)')
fig.tight_layout()
plt.grid(True)
plt.show()

ib.disconnect()
