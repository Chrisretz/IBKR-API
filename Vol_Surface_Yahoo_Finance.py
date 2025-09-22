import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import datetime as dt
from scipy.interpolate import griddata

# ----- 1) Vælg ticker -----
ticker_symbol = "NVDA"   # <-- ændr ticker her
ticker = yf.Ticker(ticker_symbol)

spot = float(ticker.history(period="1d")["Close"].iloc[-1])
expiries = ticker.options

rows = []

for expiry in expiries:
    try:
        chain = ticker.option_chain(expiry)
        calls = chain.calls.copy()
        puts  = chain.puts.copy()

        # Tid til udløb i år
        ed = dt.datetime.strptime(expiry, "%Y-%m-%d")
        T = (ed - dt.datetime.today()).days / 365
        if T <= 0: 
            continue

        # Merge calls/puts på strike
        m = pd.merge(
            calls[['strike','impliedVolatility','openInterest']],
            puts [['strike','impliedVolatility','openInterest']],
            on='strike', how='inner', suffixes=('_call','_put')
        )

        # ATM strike
        atm_strike = m.loc[(m['strike']-spot).abs().idxmin(), 'strike']

        # Vælg IV: puts under spot, calls over spot, ATM = gennemsnit
        m['iv_final'] = np.nan
        m.loc[m['strike'] <  spot, 'iv_final'] = m.loc[m['strike'] <  spot, 'impliedVolatility_put']
        m.loc[m['strike'] >  spot, 'iv_final'] = m.loc[m['strike'] >  spot, 'impliedVolatility_call']
        m.loc[m['strike'] == atm_strike, 'iv_final'] = m.loc[
            m['strike'] == atm_strike, ['impliedVolatility_call','impliedVolatility_put']
        ].mean(axis=1)

        # ATM-IV til filter
        atm_iv = m.loc[m['strike'] == atm_strike, 'iv_final'].iloc[0]

        sigma_exp = atm_iv * np.sqrt(T)
        lower = spot * (1 - 2 * sigma_exp)
        upper = spot * (1 + 2 * sigma_exp)

        # Filtrér strikes og outliers
        m = m[(m['strike'] >= lower) & (m['strike'] <= upper)]
        m = m[(m['openInterest_call'] + m['openInterest_put']) > 0]
        m = m[np.isfinite(m['iv_final'])]
        m = m[m['iv_final'] < 1.0]  # fjern IV > 100% som outliers

        if m.empty:
            continue

        # Gem data
        tmp = pd.DataFrame({
            'x': np.log(m['strike'] / spot),  # log-moneyness
            'T': T,
            'iv': m['iv_final'].values
        })
        rows.append(tmp)

    except Exception as e:
        print(f"Skip {expiry}: {e}")

# ----- 2) Saml & Interpolér -----
df = pd.concat(rows, ignore_index=True)
if df.empty:
    raise SystemExit("Ingen data tilbage efter filtrering")

# Definér grid
x_lin = np.linspace(df['x'].min(), df['x'].max(), 80)
T_lin = np.linspace(df['T'].min(), df['T'].max(), 60)
X, Y = np.meshgrid(x_lin, T_lin)

# Cubic interpolation + fallback nearest
Z_cubic = griddata(df[['x','T']].values, df['iv'].values, (X, Y), method='cubic')
Z_near  = griddata(df[['x','T']].values, df['iv'].values, (X, Y), method='nearest')
Z = np.where(np.isnan(Z_cubic), Z_near, Z_cubic)

# Konverter strikes tilbage fra log-moneyness
strikes_grid = spot * np.exp(X)

# ----- 3) Plot 3D Surface -----
fig = plt.figure(figsize=(14,6))
ax = fig.add_subplot(121, projection='3d')

surf = ax.plot_surface(strikes_grid, Y, Z, cmap='viridis', edgecolor='none')

# Tilføj spot-linje (langs hele T-aksen, på spot strike)
ax.plot([spot]*len(T_lin), T_lin, [Z.min()]*len(T_lin),
        color='red', linestyle='--', linewidth=2, label=f"Spot {spot:.2f}")

ax.set_title(f"Volatility Surface – {ticker_symbol} (Spot: {spot:.2f})")
ax.set_xlabel("Strike")
ax.set_ylabel("Time to Expiry (Years)")
ax.set_zlabel("Implied Volatility")
ax.legend()
fig.colorbar(surf, ax=ax, shrink=0.5, aspect=10)

# ----- 4) Plot 2D Contour Heatmap -----
ax2 = fig.add_subplot(122)
cont = ax2.contourf(strikes_grid, Y, Z, levels=20, cmap='viridis')
ax2.axvline(x=spot, color='red', linestyle='--', linewidth=1.5, label=f"Spot {spot:.2f}")  # Spot-linje
ax2.set_title(f"Volatility Surface – {ticker_symbol} (Contour view)")
ax2.set_xlabel("Strike")
ax2.set_ylabel("Time to Expiry (Years)")
ax2.legend()
fig.colorbar(cont, ax=ax2)

plt.tight_layout()
plt.show()
