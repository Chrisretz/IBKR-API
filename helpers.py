# helpers.py
from ib_insync import *
from config import CONFIG

ib = IB()

def connect_ib():
    """Forbinder til IBKR API."""
    ib.connect(CONFIG["host"], CONFIG["port"], clientId=CONFIG["clientId"])
    print("Connected:", ib.isConnected())
    ib.reqMarketDataType(CONFIG["marketDataType"])
    return ib

def disconnect_ib():
    """Afbryder forbindelsen."""
    ib.disconnect()
    print("Disconnected.")

def get_market_price(symbol, exchange="SMART", currency="USD"):
    """Henter seneste market price for en given aktie."""
    contract = Stock(symbol, exchange, currency)
    ticker = ib.reqMktData(contract)
    ib.sleep(2)
    return ticker.marketPrice()

def get_positions():
    """Returnerer dine åbne positioner som en liste."""
    positions = ib.positions()
    for pos in positions:
        print(f"Ticker: {pos.contract.symbol}, Qty: {pos.position}, AvgPrice: {pos.avgCost}")
    return positions

def get_account_summary():
    """Returnerer kontooversigt (NetLiquidation, BuyingPower, etc.)."""
    account_summary = ib.accountSummary()
    for item in account_summary:
        print(f"{item.tag}: {item.value} {item.currency}")
    return account_summary

# Eksempel på ordre (kan kommenteres ud indtil du vil teste)
def place_test_order(symbol="AAPL", quantity=1):
    """Placerer en market BUY-ordre (kun for test i paper trading)."""
    contract = Stock(symbol, "SMART", "USD")
    order = MarketOrder('BUY', quantity)
    trade = ib.placeOrder(contract, order)
    print("Order placed:", trade)
    return trade
