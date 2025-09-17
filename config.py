# config.py
# Her styrer du om du kører paper eller live, og hvilken port du bruger

CONFIG = {
    "host": "127.0.0.1",
    "port": 7497,      # 7497 = paper, 7496 = live
    "clientId": 1,     # kan være 1-10. Brug samme hver gang for at undgå dobbelte sessioner
    "marketDataType": 4  # 1=live, 3=frozen, 4=delayed
}
