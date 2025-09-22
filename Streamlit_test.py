import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import datetime as dt
from scipy.interpolate import griddata
import plotly.graph_objects as go
from yahooquery import search

# ========== LAYOUT & STYLING ==========
st.set_page_config(page_title="Finansielt Dashboard", layout="wide")

# Custom CSS til marginer/padding
st.markdown("""
<style>
.block-container {
    padding-top: 1rem;
    padding-bottom: 2rem;
    padding-left: 3rem;
    padding-right: 3rem;
}
</style>
""", unsafe_allow_html=True)

st.title("📊 Finansielt Dashboard")

# ========== SØGEFUNKTION ==========
st.subheader("🔍 Søg efter en aktie")

def search_tickers(query):
    try:
        result = search(query)
        if "quotes" in result:
            return [f"{item['symbol']} – {item.get('shortname', '')}" for item in result["quotes"]]
    except Exception as e:
        st.error(f"Fejl ved søgning: {e}")
    return []

search_input = st.text_input("Indtast selskabsnavn eller ticker", placeholder="F.eks. Apple, Tesla, NVDA")

ticker = None
if search_input:
    matches = search_tickers(search_input)
    if matches:
        selected = st.selectbox("Vælg en aktie fra listen", matches)
        ticker = selected.split(" – ")[0]
    else:
        st.warning("Ingen resultater fundet. Prøv et andet søgeord.")


# ========== CACHED DATAFUNKTIONS ==========
@st.cache_data(ttl=300)
def get_stock_data(ticker, period):
    data = yf.download(ticker, period=period)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.droplevel(1)
    return data

@st.cache_data(ttl=300)
def get_spot_and_expiries(ticker):
    ticker_obj = yf.Ticker(ticker)
    spot = float(ticker_obj.history(period="1d")["Close"].iloc[-1])
    expiries = ticker_obj.options
    return spot, expiries

@st.cache_data(ttl=300)
def build_vol_surface_df(ticker, spot, expiries):
    rows = []
    ticker_obj = yf.Ticker(ticker)
    for expiry in expiries:
        try:
            chain = ticker_obj.option_chain(expiry)
            calls = chain.calls.copy()
            puts = chain.puts.copy()

            ed = dt.datetime.strptime(expiry, "%Y-%m-%d")
            T = (ed - dt.datetime.today()).days / 365
            if T <= 0:
                continue

            m = pd.merge(
                calls[['strike', 'impliedVolatility', 'openInterest']],
                puts[['strike', 'impliedVolatility', 'openInterest']],
                on='strike', how='inner', suffixes=('_call', '_put')
            )

            atm_strike = m.loc[(m['strike'] - spot).abs().idxmin(), 'strike']
            m['iv_final'] = np.nan
            m.loc[m['strike'] < spot, 'iv_final'] = m.loc[m['strike'] < spot, 'impliedVolatility_put']
            m.loc[m['strike'] > spot, 'iv_final'] = m.loc[m['strike'] > spot, 'impliedVolatility_call']
            m.loc[m['strike'] == atm_strike, 'iv_final'] = m.loc[
                m['strike'] == atm_strike, ['impliedVolatility_call', 'impliedVolatility_put']
            ].mean(axis=1)

            atm_iv = m.loc[m['strike'] == atm_strike, 'iv_final'].iloc[0]
            sigma_exp = atm_iv * np.sqrt(T)
            lower = spot * (1 - 2 * sigma_exp)
            upper = spot * (1 + 2 * sigma_exp)

            m = m[(m['strike'] >= lower) & (m['strike'] <= upper)]
            m = m[(m['openInterest_call'] + m['openInterest_put']) > 0]
            m = m[np.isfinite(m['iv_final'])]
            m = m[m['iv_final'] < 1.0]

            if not m.empty:
                tmp = pd.DataFrame({
                    'x': np.log(m['strike'] / spot),
                    'T': T,
                    'iv': m['iv_final'].values
                })
                rows.append(tmp)

        except Exception:
            continue

    if rows:
        return pd.concat(rows, ignore_index=True)
    return pd.DataFrame()


# ========== KURSDATA ==========
if ticker:
    period = st.selectbox("Vælg periode", ["1d", "5d", "1mo", "6mo", "1y", "5y", "max"], index=4)
    data = get_stock_data(ticker, period)

    if not data.empty:
        st.subheader(f"Aktiekurs for {ticker}")
        data["SMA50"] = data["Close"].rolling(50).mean()
        data["SMA200"] = data["Close"].rolling(200).mean()

        show_volume = st.checkbox("Vis volumen på grafen", value=True)

        fig_price = go.Figure()
        fig_price.add_trace(go.Scatter(x=data.index, y=data["Close"], mode='lines', name='Close', line=dict(color='blue')))
        fig_price.add_trace(go.Scatter(x=data.index, y=data["SMA50"], mode='lines', name='SMA50', line=dict(color='orange', dash='dash')))
        fig_price.add_trace(go.Scatter(x=data.index, y=data["SMA200"], mode='lines', name='SMA200', line=dict(color='green', dash='dot')))

        if show_volume:
            fig_price.add_trace(go.Bar(x=data.index, y=data["Volume"], name='Volume', marker_color='rgba(150,150,150,0.4)', yaxis='y2'))

        fig_price.update_layout(
            title="Pris + SMA" + (" + Volume" if show_volume else ""),
            xaxis=dict(title="Dato"),
            yaxis=dict(title="Pris"),
            yaxis2=dict(
                title="Volumen",
                overlaying='y',
                side='right',
                showgrid=False
            ),
            bargap=0,
            height=500,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        st.plotly_chart(fig_price, use_container_width=True)

        if st.checkbox("Vis rådata"):
            st.dataframe(data.tail())


# ========== VOLATILITY SURFACE ==========
st.markdown("---")
st.subheader("📈 Volatility Surface")
show_surface = st.checkbox("Beregn og vis volatility surface", value=False)

if show_surface:
    spot, expiries = get_spot_and_expiries(ticker)

    # Mulighed for at tvinge genberegning (ignorer cache)
    force_refresh = st.button("🔄 Opdater vol surface-data")
    if force_refresh:
        st.cache_data.clear()  # Tømmer al cache

    with st.spinner("⏳ Beregner volatility surface..."):
        df = build_vol_surface_df(ticker, spot, expiries)

    if df.empty:
        st.warning("Kunne ikke beregne volatility surface (for lidt data).")
    else:
        x_lin = np.linspace(df['x'].min(), df['x'].max(), 80)
        T_lin = np.linspace(df['T'].min(), df['T'].max(), 60)
        X, Y = np.meshgrid(x_lin, T_lin)

        Z_cubic = griddata(df[['x', 'T']].values, df['iv'].values, (X, Y), method='cubic')
        Z_near = griddata(df[['x', 'T']].values, df['iv'].values, (X, Y), method='nearest')
        Z = np.where(np.isnan(Z_cubic), Z_near, Z_cubic)

        strikes_grid = spot * np.exp(X)

        col1, col2 = st.columns(2)

        with col1:
            fig3d = go.Figure()
            fig3d.add_trace(go.Surface(x=strikes_grid, y=Y, z=Z, colorscale='Viridis', showscale=True))
            fig3d.add_trace(go.Scatter3d(
                x=[spot] * len(T_lin),
                y=T_lin,
                z=[np.nanmin(Z)] * len(T_lin),
                mode='lines',
                line=dict(color='red', width=5, dash='dash'),
                name=f"Spot {spot:.2f}"
            ))
            fig3d.update_layout(
                title=f"Vol Surface 3D – {ticker}",
                scene=dict(
                    xaxis_title='Strike',
                    yaxis_title='Time to Expiry (Years)',
                    zaxis_title='Implied Volatility',
                    aspectmode='cube'
                ),
                scene_camera=dict(eye=dict(x=-1.5, y=-1.5, z=1.2)),
                height=700
            )
            st.plotly_chart(fig3d, use_container_width=True)

        with col2:
            fig2d = go.Figure(data=go.Contour(
                x=strikes_grid[0], y=T_lin, z=Z,
                colorscale='Viridis',
                contours=dict(showlabels=True)
            ))
            fig2d.add_vline(x=spot, line=dict(color='red', dash='dash'))
            fig2d.update_layout(
                title=f"Vol Surface Contour – {ticker}",
                xaxis_title='Strike',
                yaxis_title='Time to Expiry (Years)',
                height=700
            )
            st.plotly_chart(fig2d, use_container_width=True)

