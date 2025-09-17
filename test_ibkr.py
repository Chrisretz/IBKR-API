from ib_insync import *

# Opret en IB "session"
ib = IB()

# Forbind til TWS – husk at TWS skal køre og API være slået til
# 7497 = Paper trading via TWS, 7496 = Live trading via TWS
# Hvis du bruger IB Gateway, så er porten typisk 4002 (paper) eller 4001 (live)
ib.connect('127.0.0.1', 7497, clientId=1)

print("Connected:", ib.isConnected())

# Brug forsinkede data, hvis du ikke har live market data abonnement
ib.reqMarketDataType(4)  # 1=live, 3=frozen, 4=delayed

# Opret en kontrakt (Apple-aktie)
contract = Stock('AAPL', 'SMART', 'USD')

# Hent markedsdata
ticker = ib.reqMktData(contract)

# Vent et par sekunder på at data bliver hentet
ib.sleep(2)

print("Last:", ticker.last, "MarketPrice:", ticker.marketPrice())

# Hent IB serverens tid (ekstra check)
print("Server time:", ib.reqCurrentTime())

# Afbryd forbindelsen
ib.disconnect()
