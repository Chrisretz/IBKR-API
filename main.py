# main.py
from helpers import connect_ib, disconnect_ib, get_market_price, get_positions, get_account_summary
# from helpers import place_test_order  # Kun til paper trading

if __name__ == "__main__":
    ib = connect_ib()

    print("\n=== MARKET PRICE ===")
    price = get_market_price("AAPL")
    print(f"AAPL market price: {price}")

    print("\n=== ACCOUNT SUMMARY ===")
    get_account_summary()

    print("\n=== POSITIONS ===")
    get_positions()

    # Kun hvis du vil teste ordreflow (og helst i paper trading!)
    # place_test_order("AAPL", 1)

    disconnect_ib()
