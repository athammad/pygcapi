import requests
import json
from typing import Optional, Dict, Any, List, Union
import pandas as pd
from pygcapi.utils import (
    get_instruction_status_description,
    get_instruction_status_reason_description,
    get_order_status_description,
    get_order_status_reason_description,
    get_order_action_type_description,
    convert_to_dataframe,
    convert_orders_to_dataframe,
    extract_every_nth
)

class GCapiClientV1:

    """
    A client for interacting with the Gain Capital API.

    Provides methods to handle trading operations, retrieve market data, account information,
    trade history, and manage orders and positions.
    """
    BASE_URL = "https://ciapi.cityindex.com/TradingAPI"

    def __init__(self, username: str, password: str, appkey: str):
        """
        Initialize the GCapiClient object and create a session.

        :param username: The username for the Gain Capital API.
        :param password: The password for the Gain Capital API.
        :param appkey: The application key for the Gain Capital API.
        """
        self.username = username
        self.appkey = appkey
        self.session_id = None
        self.trading_account_id = None

        headers = {'Content-Type': 'application/json'}
        data = {
            "UserName": username,
            "Password": password,
            "AppKey": appkey
        }

        response = requests.post(
            f"{self.BASE_URL}/session",
            headers=headers,
            data=json.dumps(data)
        )
        if response.status_code != 200:
            raise Exception(f"Failed to create session: {response.text}")

        resp_data = response.json()
        if 'Session' not in resp_data:
            raise Exception("Login failed, session not created.")

        self.session_id = resp_data['Session']
        self.headers = {
            'Content-Type': 'application/json',
            'UserName': username,
            'Session': self.session_id
        }

    def get_account_info(self, key: Optional[str] = None) -> Any:
        """
        Retrieve account information.

        :param key: Optional key to extract specific information from the account details.
        :return: Account information as a dictionary or a specific value if a key is provided.
        """
        response = requests.get(f"{self.BASE_URL}/UserAccount/ClientAndTradingAccount", headers=self.headers)
        if response.status_code != 200:
            raise Exception(f"Failed to retrieve account info: {response.text}")

        account_info = response.json()
        self.trading_account_id = account_info.get("TradingAccounts", [{}])[0].get("TradingAccountId")

        if key:
            return account_info.get("TradingAccounts", [{}])[0].get(key)

        return account_info

    def get_market_info(self, market_name: str, key: Optional[str] = None) -> Any:
        """
        Retrieve market information based on the market name.

        :param market_name: The name of the market to retrieve information for.
        :param key: Optional key to extract specific information from the market details.
        :return: Market information as a dictionary or a specific value if a key is provided.
        """
        params = {"marketName": market_name}
        response = requests.get(f"{self.BASE_URL}/cfd/markets", headers=self.headers, params=params)

        if response.status_code != 200:
            raise Exception(f"Failed to retrieve market info: {response.text}")

        markets = response.json().get("Markets", [])
        if not markets:
            raise Exception(f"No market information found for: {market_name}")

        if key:
            return markets[0].get(key)

        return markets[0]

    def get_prices(self, market_id: str, num_ticks: int, from_ts: int, to_ts: int, price_type: str = "MID") -> pd.DataFrame:
        """
        Retrieve tick history (price data) for a specific market.

        :param market_id: The market ID for which price data is retrieved.
        :param num_ticks: The maximum number of ticks to retrieve.
        :param from_ts: Start timestamp for the data.
        :param to_ts: End timestamp for the data.
        :param price_type: The type of price data to retrieve (e.g., "MID", "BID", "ASK").
        :return: A DataFrame containing the price data.
        """
        params = {
            "fromTimeStampUTC": from_ts,
            "toTimeStampUTC": to_ts,
            "maxResults": num_ticks,
            "priceType": price_type.upper()
        }

        url = f"{self.BASE_URL}/market/{market_id}/tickhistorybetween"
        response = requests.get(url, headers=self.headers, params=params)

        if response.status_code != 200:
            raise Exception(f"Failed to retrieve prices: {response.text}")

        data = response.json()
        price_ticks = data.get("PriceTicks", [])
        if not price_ticks:
            raise Exception(f"No price data found for market ID {market_id}")

        # Rename 'TickDate' to 'BarDate' so convert_to_dataframe can handle it
        for tick in price_ticks:
            if 'TickDate' in tick:
                tick['BarDate'] = tick.pop('TickDate')

        # Convert to DataFrame with nicely formatted date
        df = convert_to_dataframe(price_ticks)
        return df

    def get_ohlc(self, 
                 market_id: str, 
                 num_ticks: int, 
                 interval: str = "HOUR", 
                 span: int = 1, 
                 from_ts: int = None, 
                 to_ts: int = None) -> pd.DataFrame:
        """
        Retrieve OHLC (Open-High-Low-Close) data for a specific market.

        :param market_id: The market ID for which OHLC data is retrieved.
        :param num_ticks: The maximum number of OHLC data points to retrieve.
        :param interval: The time interval of the OHLC data (e.g., "MINUTE", "HOUR", "DAY").
        :param span: The span size for the given interval.
        :param from_ts: Start timestamp for the data (optional).
        :param to_ts: End timestamp for the data (optional).
        :return: A DataFrame containing the OHLC data.
        """
        params = {
            "interval": interval,
            "span": span,
            "fromTimeStampUTC": from_ts,
            "toTimeStampUTC": to_ts,
            "maxResults": num_ticks
        }

        url = f"{self.BASE_URL}/market/{market_id}/barhistorybetween"
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code != 200:
            raise Exception(f"Failed to retrieve OHLC data: {response.text}")

        data = response.json()
        price_bars = data.get("PriceBars", [])
        if not price_bars:
            raise Exception(f"No OHLC data found for market ID {market_id}")

        # Convert to DataFrame with nicely formatted date
        df = convert_to_dataframe(price_bars)
        return df

    def trade_order(self, quantity: float, direction: str, market_id: str, price: float) -> Dict:
        """
        Place a trade order.

        :param quantity: The quantity of the order.
        :param direction: The direction of the trade ("buy" or "sell").
        :param market_id: The market ID where the order is placed.
        :param price: The price at which the order is placed.
        :return: The response from the API containing order details.
        """
        order = {
            "MarketId": market_id,
            "Direction": direction,
            "Quantity": quantity,
            "Price": price,
            "TradingAccountId": self.trading_account_id
        }

        response = requests.post(
            f"{self.BASE_URL}/order/newtradeorder",
            headers=self.headers,
            data=json.dumps(order)
        )

        if response.status_code != 200:
            raise Exception(f"Failed to place trade order: {response.text}")

        resp_data = response.json()
        status_desc = get_instruction_status_description(resp_data.get("StatusReason"))
        reason_desc = get_instruction_status_reason_description(resp_data.get("StatusReason"))
        print(f"Order Status: {status_desc} - {reason_desc}")

        return resp_data

    def list_open_positions(self) -> pd.DataFrame:
        """
        List all open positions.

        :return: A Data Frame containing details of open positions.
        """
        response = requests.get(f"{self.BASE_URL}/order/openpositions", headers=self.headers)
        if response.status_code != 200:
            raise Exception(f"Failed to retrieve open positions: {response.text}")

        positions = response.json()
        for position in positions.get("OpenPositions", []):
            status_desc = get_order_status_description(position.get("Status"))
            reason_desc = get_order_status_reason_description(position.get("StatusReason"))
            print(f"Position ID: {position.get('PositionId')} - Status: {status_desc} - Reason: {reason_desc}")

        return pd.DataFrame(positions["OpenPositions"])

    def list_active_orders(self) -> pd.DataFrame:
        """
        List all active orders.

        :return: A Data Frame containing details of active orders.
        """
        url = f"{self.BASE_URL}/order/activeorders"
        
        # Create the request body
        request_body = {
            "TradingAccountId": self.trading_account_id
        }

        # Define headers
        headers = {
            'Content-Type': 'application/json',
            'UserName': self.username,
            'Session': self.session_id
        }

        # Perform POST request
        response = requests.post(url, headers=headers, json=request_body)

        # Check for successful response
        if response.status_code != 200:
            raise Exception(f"Failed to retrieve active orders: {response.text}")

        orders = response.json()
        for order in orders.get("Orders", []):
            status_desc = get_order_status_description(order.get("Status"))
            reason_desc = get_order_status_reason_description(order.get("StatusReason"))
            print(f"Order ID: {order.get('OrderId')} - Status: {status_desc} - Reason: {reason_desc}")

        return convert_orders_to_dataframe(orders)

    def close_all_trades(self, tolerance: float) -> List[Dict]:
        """
        Close all open trades within a given price tolerance.

        :param tolerance: The price tolerance for closing trades.
        :return: A list of responses for each closed trade.
        """
        open_positions = self.list_open_positions().get("OpenPositions", [])

        if not open_positions:
            print("No open positions to close.")
            return []

        close_responses = []
        for position in open_positions:
            market_id = position["MarketId"]
            direction = "sell" if position["Direction"] == "buy" else "buy"
            quantity = position["Quantity"]
            # Example adjustment: adding tolerance to the price.
            close_price = position.get("Price", 0.0) + tolerance

            response = self.trade_order(
                quantity=quantity,
                direction=direction,
                market_id=market_id,
                price=close_price
            )
            close_responses.append(response)

        return close_responses

    def close_all_trades_new(self, open_positions: List[Dict], tolerance: float) -> List[Dict]:
        """
        Close all trades using a provided list of open positions and a given tolerance.

        :param open_positions: A list of open positions to close.
        :param tolerance: The price tolerance for closing trades.
        :return: A list of responses for each closed trade.
        """
        if not open_positions:
            print("No open positions to close.")
            return []

        close_responses = []
        for position in open_positions:
            market_id = position["MarketId"]
            direction = "sell" if position["Direction"] == "buy" else "buy"
            quantity = position["Quantity"]
            # Add tolerance to the price if needed
            close_price = position.get("Price", 0.0) + tolerance

            response = self.trade_order(
                quantity=quantity,
                direction=direction,
                market_id=market_id,
                price=close_price
            )
            close_responses.append(response)

        return close_responses

    def get_trade_history(self, from_ts: Optional[str] = None, max_results: int = 100) -> pd.DataFrame:
        """
        Retrieve the trade history for the account.

        :param from_ts: The start timestamp for retrieving trade history (optional).
        :param max_results: The maximum number of results to retrieve.
        :return: A DataFrame containing the trade history.
        """
 
        params = {"TradingAccountId": self.trading_account_id, "maxResults": max_results}
        if from_ts:
            params["from"] = from_ts

        response = requests.get(f"{self.BASE_URL}/order/tradehistory", headers=self.headers, params=params)
        if response.status_code != 200:
            raise Exception(f"Failed to retrieve trade history: {response.text}")

        data=pd.DataFrame(response.json()['TradeHistory'])
        return data

    def get_long_series(self, market_id: str, n_months: int = 6, by_time: str = '15min', n: int = 3900, interval: str = "MINUTE", span: int = 15) -> pd.DataFrame:
    
        """
        Retrieve a long time series of OHLC data by bypassing API limitations.
        Internally uses get_ohlc to fetch data in chunks across the specified period.

        :param market_id: The market ID for which OHLC data is fetched.
        :param n_months: Number of months of data to retrieve.
        :param by_time: The frequency (interval) used to chunk data requests (e.g., '15min', '30min', etc.).
        :param n: The maximum number of data points per request.
        :param interval: The interval of OHLC data (e.g., "MINUTE", "HOUR").
        :param span: The span size for the given interval.
        :return: A concatenated DataFrame of all the OHLC data retrieved.
        """
        time_intervals = extract_every_nth(n_months=n_months, by_time=by_time, n=n)
        long_series = []

        for start_ts, stop_ts in time_intervals:
            # Use the get_ohlc method to fetch data for each chunk
            try:
                ohlc_df = self.get_ohlc(
                    market_id=market_id,
                    num_ticks=n,
                    interval=interval,
                    span=span,
                    from_ts=start_ts,
                    to_ts=stop_ts
                )
                long_series.append(ohlc_df)
            except Exception as e:
                print(f"Failed to retrieve OHLC data for interval {start_ts} - {stop_ts}: {e}")
                continue

        # Concatenate all DataFrames if we have data
        if long_series:
            df = pd.concat(long_series, ignore_index=True)
            # Remove duplicates if any and sort by BarDate
            df = df.drop_duplicates().reset_index(drop=True)
            return df
        else:
            print("No data was retrieved.")
            return pd.DataFrame()
