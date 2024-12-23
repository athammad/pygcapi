from pygcapi.core_v1 import GCapiClientV1
from datetime import datetime, timedelta
import calendar
import keyring
import pandas as pd
# assuming keyring installed...

# Initialize the GCapiClient
client = GCapiClientV1(username= keyring.get_password("fx_system", "IDLOG"), 
                     password=keyring.get_password("fx_system", "PSWD"), 
                     appkey=keyring.get_password("fx_system", "APKEY"))


# Call get_account_info
client.get_account_info()

# Get market information
market_info = client.get_market_info("EUR/USD")
print("Market Information:", market_info)

# Retrieve specific information (e.g., MarketId and Name)
market_id = client.get_market_info("EUR/USD", key="MarketId")
market_name = client.get_market_info("EUR/USD", key="Name")
print("Market ID:", market_id)
print("Market Name:", market_name)

# Get price data for a market
from_ts = calendar.timegm((datetime.utcnow() - timedelta(days=30)).utctimetuple())  # 1 month ago
to_ts = calendar.timegm(datetime.utcnow().utctimetuple())  # Current time
prices = client.get_prices(market_id=market_id, from_ts=from_ts,to_ts=to_ts, num_ticks=1)
prices
# Get OHLC data for a market
from_ts = calendar.timegm((datetime.utcnow() - timedelta(days=1)).utctimetuple())  # 1 day ago
to_ts = calendar.timegm(datetime.utcnow().utctimetuple())  # Current time
ohlc = client.get_ohlc(market_id=market_id,from_ts=from_ts,to_ts=to_ts, num_ticks=30,span=1)
ohlc

client.get_long_series(market_id=market_id, n_months=7, by_time="30min", interval="MINUTE",span=30)


client.get_trade_history()
client.list_open_positions()
client.list_active_orders()


# To Test
# close_all_trades_new()
# close_all_trades()
# trade_order()


from pygcapi.utils import extract_every_nth, convert_to_dataframe
extract_every_nth(n_months=7, by_time="30min")


from pygcapi.core_v2 import GCapiClientV2
from datetime import datetime, timedelta
import calendar
import keyring
import pandas as pd
# Initialize the GCapiClient
client = GCapiClientV2(username= keyring.get_password("fx_system", "IDLOG"), 
                     password=keyring.get_password("fx_system", "PSWD"), 
                     appkey=keyring.get_password("fx_system", "APKEY"))

# Call get_account_info
client.get_account_info()

# Get market information
market_info = client.get_market_info("EUR/USD")
print("Market Information:", market_info)

# Retrieve specific information (e.g., MarketId and Name)
market_id = client.get_market_info("EUR/USD", key="MarketId")
market_name = client.get_market_info("EUR/USD", key="Name")
print("Market ID:", market_id)
print("Market Name:", market_name)

# Get price data for a market
from_ts = calendar.timegm((datetime.utcnow() - timedelta(days=30)).utctimetuple())  # 1 month ago
to_ts = calendar.timegm(datetime.utcnow().utctimetuple())  # Current time
prices = client.get_prices(market_id=market_id, from_ts=from_ts,to_ts=to_ts, num_ticks=1)
prices

# Get OHLC data for a market
from_ts = calendar.timegm((datetime.utcnow() - timedelta(days=1)).utctimetuple())  # 1 day ago
to_ts = calendar.timegm(datetime.utcnow().utctimetuple())  # Current time
ohlc = client.get_ohlc(market_id=market_id,from_ts=from_ts,to_ts=to_ts, num_ticks=30,span=1)
ohlc

client.get_long_series(market_id=market_id, n_months=7, by_time="30min", interval="MINUTE",span=30)


client.get_trade_history()
client.list_open_positions()
dai=client.list_active_orders()

# To Test
# close_all_trades_new()
# close_all_trades()


from pygcapi.core_v2 import GCapiClientV2
from datetime import datetime, timedelta
import calendar
import keyring
import pandas as pd
# Initialize the GCapiClient
client = GCapiClientV2(username= keyring.get_password("fx_system", "IDLOG"), 
                     password=keyring.get_password("fx_system", "PSWD"), 
                     appkey=keyring.get_password("fx_system", "APKEY"))

client.get_account_info()

market_id = client.get_market_info("EUR/USD", key="MarketId")
market_name = client.get_market_info("EUR/USD", key="Name")
print("Market ID:", market_id)
print("Market Name:", market_name)

from_ts = calendar.timegm((datetime.utcnow() - timedelta(days=30)).utctimetuple())  # 1 month ago
to_ts = calendar.timegm(datetime.utcnow().utctimetuple())  # Current time

        # Place a trade order
pricesB = client.get_prices(market_id=market_id, from_ts=from_ts,to_ts=to_ts, num_ticks=1,price_type="BID")
pricesA=client.get_prices(market_id=market_id, from_ts=from_ts,to_ts=to_ts, num_ticks=1,price_type="ASK")

trade_resp = client.trade_order(
    quantity=1020,
    direction="buy",
    market_id=market_id,
    market_name=market_name,
    bid_price=float(pricesB.Price[0]),  # Convert to scalar float
    offer_price=float(pricesA.Price[0])  # Convert to scalar float
)
print(trade_resp)

close_resp = client.trade_order(
    quantity=1020,
    direction="sell",
    close=True,
    order_id=trade_resp.get('OrderId'),
    market_id=market_id,
    market_name=market_name,
    bid_price=float(pricesB.Price[0]),  # Convert to scalar float
    offer_price=float(pricesA.Price[0])  # Convert to scalar float
)
print(trade_resp)

