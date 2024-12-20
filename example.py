from pygcapi.core import GCapiClient
import time
from datetime import datetime, timedelta
import calendar
import keyring
# assuming keyring installed...

# Initialize the GCapiClient
client = GCapiClient(username= keyring.get_password("fx_system", "IDLOG"), 
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

#ERROR HERE!!
longTS = client.get_long_series(market_id=market_id, n_months=1, by_time="30min", interval="MINUTE", span=4000)
longTS
