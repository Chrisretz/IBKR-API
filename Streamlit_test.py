import streamlit as st
import yfinance as yf
import pandas as pd

# Titel
st.title("📈 Interaktiv aktiegraf")

# Input fra brugeren
ticker = st.text_input("Indtast et ticker-symbol", value="AAPL")
period = st.selectbox("Vælg periode", ["1d", "5d", "1mo", "6mo", "1y", "5y", "max"], index=4)

# Hent data
if ticker:
    data = yf.download(ticker, period=period)

    if data.empty:
        st.warning("Kunne ikke hente data. Tjek om ticker er korrekt.")
    else:
        st.subheader(f"Aktiekurs for {ticker}")
        st.line_chart(data["Close"])

        st.write("Seneste data:")
        st.dataframe(data.tail())
