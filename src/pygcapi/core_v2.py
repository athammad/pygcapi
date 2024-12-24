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

class GCapiClientV2:
    
    """
    A client for interacting with the Gain Capital API V2.

    Provides methods to handle trading operations, retrieve market data, account information,
    trade history, and manage orders and positions.
    """
        
    BASE_URL_V1 = "https://ciapi.cityindex.com/TradingAPI"
    BASE_URL_V2 = "https://ciapi.cityindex.com/v2"

    def __init__(self, username: str, password: str, appkey: str):
        """
        Initialize the GCapiClientV2 object and create a session.

        :param username: The username for the Gain Capital API.
        :param password: The password for the Gain Capital API.
        :param appkey: The application key for the Gain Capital API.
        """
        self.username = username
        self.appkey = appkey
        self.session_id = None
        self.trading_account_id = None
        self.client_account_id = None

        headers = {'Content-Type': 'application/json'}
        data = {
            "UserName": username,
            "Password": password,
            "AppKey": appkey
        }

        response = requests.post(
            f"{self.BASE_URL_V2}/session",
            headers=headers,
            data=json.dumps(data)
        )
        if response.status_code != 200:
            raise Exception(f"Failed to create session: {response.text}")

        resp_data = response.json()
        if 'session' not in resp_data:
            raise Exception("Login failed, session not created.")

        self.session_id = resp_data['session']
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
        response = requests.get(f"{self.BASE_URL_V2}/UserAccount/ClientAndTradingAccount", headers=self.headers)
        if response.status_code != 200:
            raise Exception(f"Failed to retrieve account info: {response.text}")

        account_info = response.json()
        self.trading_account_id = account_info.get("tradingAccounts", [{}])[0].get("tradingAccountId")
        self.client_account_id = account_info.get("tradingAccounts", [{}])[0].get("clientAccountId")

        if key:
            return account_info.get("TradingAccounts", [{}])[0].get(key)

        return account_info

    def get_market_info(self, market_name: str, key: Optional[str] = None) -> Any:
        """
        Retrieve market information.

        :param market_name: The name of the market to retrieve information for.
        :param key: Optional key to extract specific information from the market details.
        :return: Market information as a dictionary or a specific value if a key is provided.
        """
        params = {"marketName": market_name}
        response = requests.get(f"{self.BASE_URL_V1}/cfd/markets", headers=self.headers, params=params)

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

        url = f"{self.BASE_URL_V1}/market/{market_id}/tickhistorybetween"
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

    def get_ohlc(self, market_id: str, num_ticks: int, interval: str = "HOUR", span: int = 1, from_ts: int = None, to_ts: int = None) -> pd.DataFrame:
        """
        Retrieve OHLC data for a specific market.

        :param market_id: The market ID for which OHLC data is retrieved.
        :param num_ticks: The maximum number of OHLC data points to retrieve.
        :param interval: The time interval of the OHLC data (e.g., "MINUTE", "HOUR", "DAY").
        :param span: The span size for the given interval.
        :param from_ts: Start timestamp for the data.
        :param to_ts: End timestamp for the data.
        :return: A DataFrame containing the OHLC data.
        """
        params = {
            "interval": interval,
            "span": span,
            "fromTimeStampUTC": from_ts,
            "toTimeStampUTC": to_ts,
            "maxResults": num_ticks
        }

        url = f"{self.BASE_URL_V1}/market/{market_id}/barhistorybetween"
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

    def trade_order(
        self,
        quantity: float,
        offer_price: float,
        bid_price: float,
        direction: str,
        market_id: str,
        market_name: str,
        stop_loss: float = None,
        take_profit: float = None,
        trigger_price: float = None,
        close: bool = False,
        order_id: str = None,
        tolerance: float = None,
    ) -> dict:
        """
        Place a trade order.

        :param quantity: Quantity to trade.
        :param offer_price: Offer price for the trade.
        :param bid_price: Bid price for the trade.
        :param direction: Direction of the trade ("buy" or "sell").
        :param market_id: Market ID.
        :param market_name: Market name.
        :param stop_loss: Stop loss price (optional).
        :param take_profit: Take profit price (optional).
        :param trigger_price: Trigger price (optional).
        :param close: Whether to close the trade (optional).
        :param order_id: Order ID (optional).
        :param tolerance: Price tolerance (optional).
        :return: API response as a dictionary.
        """
        endpoint = "/order/newtradeorder"

        # Adjust bid and offer prices based on tolerance
        if tolerance is not None:
            bid_price -= tolerance * 0.0001
            offer_price += tolerance * 0.0001

        order_details = {
            "MarketId": market_id,
            "Direction": direction,
            "Quantity": quantity,
            "OfferPrice": offer_price,
            "BidPrice": bid_price,
            "TradingAccountId": self.trading_account_id,
            "MarketName": market_name,
            "AutoRollover": False,
            "IfDone": [],
            "OcoOrder": None,
            "Type": None,
            "ExpiryDateTimeUTC": None,
            "Applicability": None,
            "TriggerPrice": trigger_price,
            "PositionMethodId": 1,
            "isTrade": True,
            "ClientAccountId": self.client_account_id,
        }

        if close:
            order_details["Close"] = {"OrderId": order_id}

        if stop_loss or take_profit:
            ifdone_order = {
                "StopOrder": {
                    "Price": stop_loss,
                    "Type": "stop",
                    "Applicability": "gtc",
                    "StopType": "loss",
                } if stop_loss else None,
                "LimitOrder": {
                    "Price": take_profit,
                    "Type": "limit",
                    "Applicability": "gtc",
                } if take_profit else None,
            }
            order_details["IfDone"].append(ifdone_order)

        body = json.dumps(order_details)

        response = requests.post(
            f"{self.BASE_URL_V1}{endpoint}",
            headers=self.headers,
            data=body,
        )

        if response.status_code != 200:
            raise Exception(f"Failed to place trade order: {response.text}")

        resp = response.json()
        print(resp)
        status_desc = get_instruction_status_description(resp.get("StatusReason"))
        reason_desc = get_instruction_status_reason_description(resp.get("StatusReason"))
        print(f"Order Status: {status_desc} - {reason_desc}")

        if "Orders" in resp:
            order_status_desc = get_order_status_description(resp["Orders"][0].get("StatusReason"))
            order_reason_desc = get_order_status_reason_description(resp["Orders"][0].get("StatusReason"))
            print(f"Order Status: {order_status_desc} - {order_reason_desc}")

            if "Actions" in resp and len(resp["Actions"]) != 0:
                order_action_type = get_order_action_type_description(resp["Actions"][0].get("OrderActionTypeId"))
                print(f"Action: {order_action_type}")

            order_details["OrderId"] = resp["Orders"][0].get("OrderId")

        return order_details

    def list_open_positions(self) -> pd.DataFrame:
        """
        List all open positions.

        :return: A Data Frame containing all open positions.
        """
        response = requests.get(f"{self.BASE_URL_V1}/order/openpositions", headers=self.headers)
        if response.status_code != 200:
            raise Exception(f"Failed to retrieve open positions: {response.text}")

        positions = response.json()
        for position in positions.get("OpenPositions", []):
            status_desc = get_order_status_description(position.get("Status"))
            reason_desc = get_order_status_reason_description(position.get("StatusReason"))
            print(f"Position ID: {position.get('PositionId')} - Status: {status_desc} - Reason: {reason_desc}")

        return pd.DataFrame(positions["OpenPositions"])


    def get_trade_history(self, from_ts: Optional[str] = None, max_results: int = 100) -> pd.DataFrame:
        """
        Retrieve the trade history for the account.

        :param from_ts: Optional start timestamp for the history.
        :param max_results: Maximum number of results to retrieve.
        :return: A dictionary containing the trade history.
        """
        params = {"TradingAccountId": self.trading_account_id, "maxResults": max_results}
        if from_ts:
            params["from"] = from_ts

        response = requests.get(f"{self.BASE_URL_V1}/order/tradehistory", headers=self.headers, params=params)
        if response.status_code != 200:
            raise Exception(f"Failed to retrieve trade history: {response.text}")

        return pd.DataFrame(response.json()['TradeHistory'])

    def close_all_trades(self, tolerance: float) -> List[Dict]:
        """
        Close all open trades with a given price tolerance.

        :param tolerance: The price tolerance for closing trades.
        :return: A list of responses from the API for each trade closure.
        """
        # Get all open positions
        open_positions = self.list_open_positions()

        if open_positions.empty:
            print("No open positions to close.")
            return []

        close_responses = []

        for _, position in open_positions.iterrows():
            market_id = position["MarketId"]
            market_name = position["MarketName"]
            direction = "sell" if position["Direction"] == "buy" else "buy"
            quantity = position["Quantity"]
            order_id = position["OrderId"]  # Include OrderId for closing the trade
            bid_price = position.get("Price", 0.0)  # Assuming `Price` is the current price
            offer_price = bid_price  # Use the same price as both bid and offer initially

            # Adjust bid and offer prices based on tolerance
            if tolerance is not None:
                bid_price -= tolerance * 0.0001
                offer_price += tolerance * 0.0001

            # Close the trade
            try:
                response = self.trade_order(
                    quantity=quantity,
                    offer_price=offer_price,
                    bid_price=bid_price,
                    direction=direction,
                    market_id=market_id,
                    market_name=market_name,
                    close=True,
                    order_id=order_id,  # Pass the order_id for closing the trade
                    tolerance=tolerance,
                )
                close_responses.append(response)
                print(f"Closed trade for MarketId: {market_id}, OrderId: {order_id}, Response: {response}")

            except Exception as e:
                print(f"Failed to close trade for MarketId: {market_id}, OrderId: {order_id}. Error: {str(e)}")

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


    def list_active_orders(self) -> pd.DataFrame:
        """
        List all active orders.

        :return: A Data Frame containing details of active orders.
        """
        url = f"{self.BASE_URL_V1}/order/activeorders"
        
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

