from helpers import connect_ib, disconnect_ib, ib
from ib_insync import Stock, util
import matplotlib.pyplot as plt

def plot_stock(ticker: str, exchange: str = "SMART", currency: str = "USD"):
    """
    Henter 5 års historiske data for en given ticker og plottet kursudviklingen.
    """
    # Forbind til IBKR
    connect_ib()

    # Opret kontrakt
    contract = Stock(ticker, exchange, currency)

    # Hent kontraktdetaljer for at få selskabsnavn
    details = ib.reqContractDetails(contract)
    if details:
        company_name = details[0].longName
    else:
        company_name = ticker  # fallback, hvis ingen detaljer returneres

    # Hent historiske data (5 år, daglige lukkepriser)
    bars = ib.reqHistoricalData(
        contract,
        endDateTime='',
        durationStr='5 Y',
        barSizeSetting='1 day',
        whatToShow='TRADES',
        useRTH=True,
        formatDate=1
    )

    # Konverter til Pandas DataFrame
    df = util.df(bars)

    if df.empty:
        print(f"⚠️ Ingen data hentet for {ticker}. Tjek ticker/marketdata-abonnement.")
    else:
        # Plot i matplotlib
        plt.figure(figsize=(12, 6))
        plt.plot(df['date'], df['close'], label=f'{ticker} Close Price')
        plt.title(f'{company_name} ({ticker}) - Last 5 Years')
        plt.xlabel('Date')
        plt.ylabel(f'Close Price ({currency})')
        plt.grid()
        plt.legend()
        plt.tight_layout()
        plt.show()

    # Afbryd forbindelsen
    disconnect_ib()


if __name__ == "__main__":
    ticker = input("Indtast ticker (fx AAPL, NVDA, NVO): ").strip().upper()
    plot_stock(ticker)
