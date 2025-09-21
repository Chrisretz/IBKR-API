import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from qfin.options import BlackScholesCall
from scipy.optimize import brentq

# Parametre
S = 100
r = 0.01

# Definer strikes og maturities
strikes = np.linspace(80, 120, 20)
maturities = np.linspace(0.05, 1, 20)

# Opret meshgrid
K, T = np.meshgrid(strikes, maturities)

# "Fake" market prices: antag at vol afhænger af strike (volatility smile)
true_iv = 0.25 + 0.0015 * (K - S)**2 / S  # mere vol for strikes langt væk fra spot
market_prices = np.zeros_like(K)

for i in range(K.shape[0]):
    for j in range(K.shape[1]):
        option = BlackScholesCall(S, true_iv[i, j], K[i, j], T[i, j], r)
        market_prices[i, j] = option.price

# Funktion til at beregne implied volatility ved root-finding
def implied_vol(price, S, K, T, r):
    def objective(sigma):
        return BlackScholesCall(S, sigma, K, T, r).price - price
    
    try:
        return brentq(objective, 1e-6, 5.0)  # søg mellem næsten 0% og 500% vol
    except ValueError:
        return np.nan  # hvis ingen løsning findes

# Beregn implied vol surface
implied_vol_surface = np.zeros_like(K)
for i in range(K.shape[0]):
    for j in range(K.shape[1]):
        implied_vol_surface[i, j] = implied_vol(market_prices[i, j], S, K[i, j], T[i, j], r)

# Plot IV surface
fig = plt.figure(figsize=(10, 6))
ax = fig.add_subplot(111, projection='3d')
surf = ax.plot_surface(K, T, implied_vol_surface, cmap='plasma')

ax.set_xlabel('Strike')
ax.set_ylabel('Tid til udløb (år)')
ax.set_zlabel('Implied Volatility')
ax.set_title('Implied Volatility Surface (Synthetic)')
fig.colorbar(surf, shrink=0.5, aspect=10)
plt.show()
