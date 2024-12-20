import requests
import json
from typing import Optional, Dict, Any, List
from pygcapi.utils import (
    get_instruction_status_description,
    get_instruction_status_reason_description,
    get_order_status_description,
    get_order_status_reason_description,
    get_order_action_type_description,
    extract_every_nth
)

class GCapiClient:
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
        :return: Account information or specific value if key is provided.
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
        Retrieve market information.

        :param market_name: The name of the market to retrieve information for.
        :param key: Optional key to extract specific information from the market details.
        :return: Market information or specific value if key is provided.
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

    def trade_order(self, quantity: float, direction: str, market_id: str, price: float) -> Dict:
        """
        Place a trade order.

        :param quantity: The quantity of the trade.
        :param direction: The trade direction, either "buy" or "sell".
        :param market_id: The ID of the market to trade on.
        :param price: The price at which to execute the trade.
        :return: Response from the API containing trade details.
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

    def list_open_positions(self) -> Dict:
        """
        List all open positions.

        :return: A dictionary containing open positions.
        """
        response = requests.get(f"{self.BASE_URL}/order/openpositions", headers=self.headers)
        if response.status_code != 200:
            raise Exception(f"Failed to retrieve open positions: {response.text}")

        positions = response.json()
        for position in positions.get("OpenPositions", []):
            status_desc = get_order_status_description(position.get("Status"))
            reason_desc = get_order_status_reason_description(position.get("StatusReason"))
            print(f"Position ID: {position.get('PositionId')} - Status: {status_desc} - Reason: {reason_desc}")

        return positions

    def list_active_orders(self) -> Dict:
        """
        List all active orders.

        :return: A dictionary containing active orders.
        """
        response = requests.get(f"{self.BASE_URL}/order/activeorders", headers=self.headers)
        if response.status_code != 200:
            raise Exception(f"Failed to retrieve active orders: {response.text}")

        orders = response.json()
        for order in orders.get("Orders", []):
            status_desc = get_order_status_description(order.get("Status"))
            reason_desc = get_order_status_reason_description(order.get("StatusReason"))
            print(f"Order ID: {order.get('OrderId')} - Status: {status_desc} - Reason: {reason_desc}")

        return orders

    def close_all_trades(self, tolerance: float) -> List[Dict]:
        """
        Close all open trades with a given price tolerance.

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
            order_id = position["OrderId"]
            market_name = position["MarketName"]

            response = self.trade_order(
                quantity=quantity,
                direction=direction,
                market_id=market_id,
                price=position.get("Price", 0.0) + tolerance  # Example adjustment
            )
            close_responses.append(response)

        return close_responses

    def get_trade_history(self, from_ts: Optional[str] = None, max_results: int = 100) -> Dict:
        """
        Retrieve the trade history for the account.

        :param from_ts: Optional timestamp to filter trades starting from a specific time.
        :param max_results: Maximum number of results to retrieve.
        :return: A dictionary containing trade history data.
        """
        params = {"TradingAccountId": self.trading_account_id, "maxResults": max_results}
        if from_ts:
            params["from"] = from_ts

        response = requests.get(f"{self.BASE_URL}/order/tradehistory", headers=self.headers, params=params)
        if response.status_code != 200:
            raise Exception(f"Failed to retrieve trade history: {response.text}")

        return response.json()

    def get_long_series(self, market_id: str, n_months: int = 6, by_time: str = '15min', n: int = 3900, interval: str = "MINUTE", span: int = 15) -> List[Dict]:
        """
        Retrieve long series data by bypassing API limitations.

        :param market_id: The market ID to retrieve data for.
        :param n_months: Number of months of data to retrieve.
        :param by_time: Time interval for data extraction (e.g., '15min').
        :param n: Maximum number of data points per request.
        :param interval: Time interval for OHLC data (e.g., "MINUTE", "HOUR").
        :param span: Span of the interval.
        :return: A list of dictionaries containing the long series data.
        """
        time_intervals = extract_every_nth(n_months=n_months, by_time=by_time, n=n)
        long_series = []

        for start, stop in time_intervals:
            params = {
                "MarketId": market_id,
                "interval": interval,
                "span": span,
                "fromTimeStampUTC": start,
                "toTimeStampUTC": stop,
                "maxResults": n
            }
            response = requests.get(f"{self.BASE_URL}/market/barhistorybetween", headers=self.headers, params=params)
            if response.status_code != 200:
                print(f"Failed to retrieve data for interval {start} - {stop}: {response.text}")
                continue

            data = response.json().get("PriceBars", [])
            long_series.extend(data)

        return long_series
