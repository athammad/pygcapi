

# pygcapi <img src="./logo_pygcapi.png" align="right" height="200"/>

The **pygcapi** Python library provides an interface to the **Gain Capital API** (V1 and V2), allowing users to perform various trading operations on [Forex.com](https://forex.com). This library includes functionalities for account management, market information retrieval, trading operations, and historical data extraction. It also includes helper utilities and lookup tables to facilitate the interpretation of API responses.

By leveraging the extensive Python ecosystem—which includes libraries for data manipulation, scientific computing, and machine learning—**pygcapi** offers a robust solution for traders and data scientists seeking to enhance their trading operations and develop automated trading strategies.

## Features

- **Account Management**: Initialize sessions and manage user accounts.
- **Market Information**: Retrieve real-time market data and details.
- **Trading Operations**: Execute trades, manage orders, and track positions.
- **Historical Data**: Extract and analyze historical market data.
- **Helper Functions**: Utilize various helper functions and lookup tables for easier API response interpretation.

## Installation
You can install this package directly from PyPI using `pip`:

```bash
pip install pygcapi
```
Or from GitHub:

```bash
pip install git+https://github.com/athammad/pygcapi.git
```

# API Credentials

To access your trading account, you will need credentials provided by Forex.com, including a username, password, and appkey. Once obtained, you can use these credentials to initialize a session with GCapiClient:


```python
from pygcapi.coreV1 import GCapiClient

# Replace with your actual credentials
IDLOG = "your_username"
PSWD = "your_password"
APKEY = "your_appkey"

client = GCapiClient(username=IDLOG, password=PSWD, appkey=APKEY)
```

# Example Usage

Retrieve Account Information:

```python
account_info = client.get_account_info()
print(account_info)

# Retrieve a specific field (e.g., TradingAccountId)
trading_account_id = client.get_account_info(key="TradingAccountId")
print(trading_account_id)
```
**Get Market Information:**

```python
market_info = client.get_market_info("EUR/USD")
print(market_info)

market_id = client.get_market_info("EUR/USD", key="MarketId")
market_name = client.get_market_info("EUR/USD", key="Name")
print(market_id)
print(market_name)

#Retrieve Price Data

import time
import datetime
from datetime import timedelta

# Define time period

one_month_ago = int((datetime.datetime.utcnow() - timedelta(days=30)).timestamp())
now = int(datetime.datetime.utcnow().timestamp())

prices = client.get_prices(
    market_id=market_id,
    num_ticks=100,
    from_ts=one_month_ago,
    to_ts=now,
    price_type="MID"
)
print(prices.head())


#Retrieve OHLC Data

one_day_ago = int((datetime.datetime.utcnow() - timedelta(days=1)).timestamp())

ohlc = client.get_ohlc(
    market_id=market_id,
    num_ticks=4000,
    interval="MINUTE",
    span=30,
    from_ts=one_day_ago,
    to_ts=now
)
print(ohlc.head())

# Place a Trade Order:

trade_resp = client.trade_order(
    quantity=1020,
    direction="buy",
    market_id=market_id,
    price=current_price
)
print(trade_resp)

#List Open Positions:

open_positions = client.list_open_positions()
print(open_positions)

#Close All Trades:

close_responses = client.close_all_trades(tolerance=0.0005)
print(close_responses)

#Retrieve Trade History:

trade_history = client.get_trade_history(max_results=50)
print(trade_history)
```
## Getting Help or Reporting an Issue

To report bugs/issues/feature requests, please file an [issue](https://github.com/athammad/pygcapi/issues/).

## Author
`rgcapi` is written by [Ahmed T. Hammad](https://athsas.com/) and is under active development. Please feel free to contribute by submitting any issues or requests—or by solving any current issues!


## Disclaimer
This package is not supported by `Forex.com`, and the author does not hold any responsibility for how users decide to use the library. Use it at your own risk.


## Official API documentation

https://docs.labs.gaincapital.com/index.html

T0 DO:
- Structure repo for python lib✅ 
- Write Class V2
- Tests
- Write Documentation
- Write examples/demo
- Logo 

✅ ❌✔✗
