import requests
import json
from typing import Optional, Dict, Any, List, Union
import pandas as pd

from pygcapi.utils import (
    get_instruction_status_description,
    get_instruction_status_reason_description,
    get_order_status_description,
    get_order_status_reason_description,
    convert_to_dataframe
)

class GCapiClientV2:
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
        response = requests.get(f"{self.BASE_URL_V2}/UserAccount/ClientAndTradingAccount", headers=self.headers)
        if response.status_code != 200:
            raise Exception(f"Failed to retrieve account info: {response.text}")

        account_info = response.json()
        self.trading_account_id = account_info.get("TradingAccounts", [{}])[0].get("TradingAccountId")
        self.client_account_id = account_info.get("TradingAccounts", [{}])[0].get("ClientAccountId")

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

    def trade_order(self, quantity: float, direction: str, market_id: str, price: float) -> Dict:
        """
        Place a trade order.

        :param quantity: The quantity of the order.
        :param direction: The direction of the trade ("buy" or "sell").
        :param market_id: The market ID for the trade.
        :param price: The price at which to place the trade.
        :return: Response from the API as a dictionary.
        """
        order = {
            "MarketId": market_id,
            "Direction": direction,
            "Quantity": quantity,
            "Price": price,
            "TradingAccountId": self.trading_account_id
        }

        response = requests.post(
            f"{self.BASE_URL_V1}/order/newtradeorder",
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

    def list_open_positions(self) -> Dict:
        """
        List all open positions.

        :return: A dictionary containing all open positions.
        """
        response = requests.get(f"{self.BASE_URL_V1}/order/openpositions", headers=self.headers)
        if response.status_code != 200:
            raise Exception(f"Failed to retrieve open positions: {response.text}")

        positions = response.json()
        for position in positions.get("OpenPositions", []):
            status_desc = get_order_status_description(position.get("Status"))
            reason_desc = get_order_status_reason_description(position.get("StatusReason"))
            print(f"Position ID: {position.get('PositionId')} - Status: {status_desc} - Reason: {reason_desc}")

        return positions

    def get_trade_history(self, from_ts: Optional[str] = None, max_results: int = 100) -> Dict:
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

        return response.json()

    def close_all_trades(self, tolerance: float) -> List[Dict]:
        """
        Close all open trades with a given price tolerance.

        :param tolerance: The price tolerance for closing trades.
        :return: A list of responses from the API for each trade closure.
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
            close_price = position.get("Price", 0.0) + tolerance

            response = self.trade_order(
                quantity=quantity,
                direction=direction,
                market_id=market_id,
                price=close_price
            )
            close_responses.append(response)

        return close_responses
