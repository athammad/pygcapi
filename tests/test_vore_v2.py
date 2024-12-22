# tests/test_core.py

import json
import pytest
import pandas as pd

try:
    import requests_mock  # This library is required for these examples
except ImportError:
    raise ImportError("Please install requests-mock via `pip install requests-mock`.")

# Import the GCapiClient from your coreV1 module
from src.pygcapi.core_v1 import GCapiClient


@pytest.fixture
def mock_gcapi_base_url():
    """
    A fixture for the base URL used by the GCapiClient.
    Modify this if your tests need to point to a different or local endpoint.
    """
    return "https://ciapi.cityindex.com/TradingAPI"


@pytest.fixture
def mock_client(mock_gcapi_base_url, requests_mock):
    """
    A fixture that sets up GCapiClient with a mock session creation.
    Returns a GCapiClient instance that can be used in tests.
    """
    # Mock the session creation POST request
    requests_mock.post(
        f"{mock_gcapi_base_url}/session",
        json={"Session": "mockSessionID"},
        status_code=200
    )

    client = GCapiClient(
        username="testuser",
        password="testpass",
        appkey="testkey"
    )
    return client


def test_init_session_failure(mock_gcapi_base_url, requests_mock):
    """
    Test that an exception is raised if session creation fails.
    """
    requests_mock.post(
        f"{mock_gcapi_base_url}/session",
        text="Invalid credentials",
        status_code=401
    )
    
    with pytest.raises(Exception) as excinfo:
        _ = GCapiClient("invalid_user", "invalid_pass", "invalid_key")
    assert "Failed to create session" in str(excinfo.value)


def test_init_success(mock_client):
    """
    Test that the client is successfully initialized with the expected session ID.
    """
    assert mock_client.session_id == "mockSessionID", "Session ID should match the mock."


def test_get_account_info_success(mock_client, requests_mock, mock_gcapi_base_url):
    """
    Test that get_account_info returns parsed JSON when the API call is successful.
    """
    mock_response = {
        "TradingAccounts": [
            {"TradingAccountId": 12345, "OtherField": "test"}
        ]
    }

    requests_mock.get(
        f"{mock_gcapi_base_url}/UserAccount/ClientAndTradingAccount",
        json=mock_response,
        status_code=200
    )

    result = mock_client.get_account_info()
    assert result == mock_response, "Expected the exact JSON response."
    assert mock_client.trading_account_id == 12345, "Should store the TradingAccountId internally."

    # Test extracting a specific key
    key_result = mock_client.get_account_info(key="OtherField")
    assert key_result == "test"


def test_get_account_info_failure(mock_client, requests_mock, mock_gcapi_base_url):
    """
    Test that an exception is raised if account info retrieval fails.
    """
    requests_mock.get(
        f"{mock_gcapi_base_url}/UserAccount/ClientAndTradingAccount",
        text="Something went wrong",
        status_code=500
    )

    with pytest.raises(Exception) as excinfo:
        mock_client.get_account_info()
    assert "Failed to retrieve account info" in str(excinfo.value)


def test_get_market_info_success(mock_client, requests_mock, mock_gcapi_base_url):
    """
    Test that get_market_info returns the first market entry from the 'Markets' array.
    """
    mock_response = {
        "Markets": [
            {"MarketId": 999, "Name": "TestMarket", "SomeKey": "SomeValue"}
        ]
    }
    requests_mock.get(
        f"{mock_gcapi_base_url}/cfd/markets",
        json=mock_response,
        status_code=200
    )

    result = mock_client.get_market_info("TestMarket")
    assert result == mock_response["Markets"][0], "Should return the first dict inside 'Markets'."

    # Test extracting a specific key
    assert mock_client.get_market_info("TestMarket", key="SomeKey") == "SomeValue"


def test_get_market_info_failure_no_market(mock_client, requests_mock, mock_gcapi_base_url):
    """
    Test that an exception is raised if no markets are returned.
    """
    mock_response = {"Markets": []}
    requests_mock.get(
        f"{mock_gcapi_base_url}/cfd/markets",
        json=mock_response,
        status_code=200
    )

    with pytest.raises(Exception) as excinfo:
        mock_client.get_market_info("UnknownMarket")
    assert "No market information found" in str(excinfo.value)


def test_get_prices_success(mock_client, requests_mock, mock_gcapi_base_url):
    """
    Test that get_prices returns a DataFrame with converted timestamps.
    """
    mock_response = {
        "PriceTicks": [
            {"TickDate": "/Date(1732075200000)/", "Price": 1.2345},
            {"TickDate": "/Date(1732075260000)/", "Price": 1.2350},
        ]
    }

    requests_mock.get(
        f"{mock_gcapi_base_url}/market/123/tickhistorybetween",
        json=mock_response,
        status_code=200
    )

    df = mock_client.get_prices(
        market_id="123",
        num_ticks=10,
        from_ts=1000000,
        to_ts=2000000,
        price_type="MID"
    )
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert "Date" in df.columns
    assert "Price" in df.columns


def test_get_prices_failure(mock_client, requests_mock, mock_gcapi_base_url):
    """
    Test that an exception is raised if price data retrieval fails.
    """
    requests_mock.get(
        f"{mock_gcapi_base_url}/market/123/tickhistorybetween",
        text="Server error",
        status_code=500
    )

    with pytest.raises(Exception) as excinfo:
        mock_client.get_prices(
            market_id="123",
            num_ticks=10,
            from_ts=1000000,
            to_ts=2000000
        )
    assert "Failed to retrieve prices" in str(excinfo.value)


def test_get_prices_no_data(mock_client, requests_mock, mock_gcapi_base_url):
    """
    Test that an exception is raised if no 'PriceTicks' are returned.
    """
    requests_mock.get(
        f"{mock_gcapi_base_url}/market/123/tickhistorybetween",
        json={"PriceTicks": []},
        status_code=200
    )

    with pytest.raises(Exception) as excinfo:
        mock_client.get_prices("123", 10, 1000000, 2000000)
    assert "No price data found" in str(excinfo.value)


def test_get_ohlc_success(mock_client, requests_mock, mock_gcapi_base_url):
    """
    Test that get_ohlc returns a DataFrame of OHLC data.
    """
    mock_response = {
        "PriceBars": [
            {"BarDate": "/Date(1732075200000)/", "Open": 1.1, "High": 1.2, "Low": 1.0, "Close": 1.15},
            {"BarDate": "/Date(1732075260000)/", "Open": 1.15, "High": 1.25, "Low": 1.1, "Close": 1.2},
        ]
    }
    requests_mock.get(
        f"{mock_gcapi_base_url}/market/123/barhistorybetween",
        json=mock_response,
        status_code=200
    )

    df = mock_client.get_ohlc("123", 10, "HOUR", 1, 1000000, 2000000)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert "Open" in df.columns and "Close" in df.columns


def test_get_ohlc_failure(mock_client, requests_mock, mock_gcapi_base_url):
    """
    Test that an exception is raised if OHLC data retrieval fails.
    """
    requests_mock.get(
        f"{mock_gcapi_base_url}/market/123/barhistorybetween",
        text="Server error",
        status_code=500
    )

    with pytest.raises(Exception) as excinfo:
        mock_client.get_ohlc("123", 10)
    assert "Failed to retrieve OHLC data" in str(excinfo.value)


def test_trade_order_success(mock_client, requests_mock, mock_gcapi_base_url):
    """
    Test placing a trade order and receiving a valid response.
    """
    mock_response = {
        "StatusReason": "1",
        "OrderId": 999
    }
    requests_mock.post(
        f"{mock_gcapi_base_url}/order/newtradeorder",
        json=mock_response,
        status_code=200
    )

    resp_data = mock_client.trade_order(
        quantity=10.0,
        direction="buy",
        market_id="999",
        price=1.2345
    )
    assert resp_data == mock_response
    assert resp_data["OrderId"] == 999


def test_trade_order_failure(mock_client, requests_mock, mock_gcapi_base_url):
    """
    Test that an exception is raised if a trade order fails.
    """
    requests_mock.post(
        f"{mock_gcapi_base_url}/order/newtradeorder",
        text="Unable to place order",
        status_code=400
    )

    with pytest.raises(Exception) as excinfo:
        mock_client.trade_order(
            quantity=10.0,
            direction="buy",
            market_id="999",
            price=1.2345
        )
    assert "Failed to place trade order" in str(excinfo.value)


def test_list_open_positions_success(mock_client, requests_mock, mock_gcapi_base_url):
    """
    Test retrieving open positions with valid data.
    """
    mock_response = {
        "OpenPositions": [
            {"PositionId": 111, "Status": "1", "StatusReason": "1", "Quantity": 10},
            {"PositionId": 222, "Status": "3", "StatusReason": "40", "Quantity": 5},
        ]
    }
    requests_mock.get(
        f"{mock_gcapi_base_url}/order/openpositions",
        json=mock_response,
        status_code=200
    )

    positions = mock_client.list_open_positions()
    assert positions == mock_response


def test_list_open_positions_failure(mock_client, requests_mock, mock_gcapi_base_url):
    """
    Test that an exception is raised if open positions retrieval fails.
    """
    requests_mock.get(
        f"{mock_gcapi_base_url}/order/openpositions",
        text="Error retrieving",
        status_code=500
    )

    with pytest.raises(Exception) as excinfo:
        mock_client.list_open_positions()
    assert "Failed to retrieve open positions" in str(excinfo.value)


def test_list_active_orders_success(mock_client, requests_mock, mock_gcapi_base_url):
    """
    Test retrieving active orders with valid data.
    """
    mock_response = {
        "Orders": [
            {"OrderId": 1234, "Status": "1", "StatusReason": "1"},
            {"OrderId": 5678, "Status": "9", "StatusReason": "70"}
        ]
    }
    requests_mock.post(
        f"{mock_gcapi_base_url}/order/activeorders",
        json=mock_response,
        status_code=200
    )

    orders = mock_client.list_active_orders()
    assert orders == mock_response


def test_list_active_orders_failure(mock_client, requests_mock, mock_gcapi_base_url):
    """
    Test that an exception is raised if active orders retrieval fails.
    """
    requests_mock.post(
        f"{mock_gcapi_base_url}/order/activeorders",
        text="Some error",
        status_code=400
    )
    
    with pytest.raises(Exception) as excinfo:
        mock_client.list_active_orders()
    assert "Failed to retrieve active orders" in str(excinfo.value)


def test_close_all_trades_no_positions(mock_client, requests_mock):
    """
    Test close_all_trades when no positions are open. Expect an empty list.
    """
    # Mocking list_open_positions to return no open positions
    mock_no_positions = {"OpenPositions": []}
    requests_mock.get(
        f"{mock_client.BASE_URL}/order/openpositions",
        json=mock_no_positions,
        status_code=200
    )

    result = mock_client.close_all_trades(tolerance=0.1)
    assert result == [], "No open positions should return an empty list."


def test_close_all_trades_with_positions(mock_client, requests_mock):
    """
    Test close_all_trades to ensure it calls trade_order for each open position.
    """
    mock_positions = {
        "OpenPositions": [
            {"PositionId": 111, "MarketId": "999", "Direction": "buy", "Quantity": 10, "Price": 1.0},
            {"PositionId": 222, "MarketId": "888", "Direction": "sell", "Quantity": 5,  "Price": 2.0},
        ]
    }
    requests_mock.get(
        f"{mock_client.BASE_URL}/order/openpositions",
        json=mock_positions,
        status_code=200
    )
    # Mock the order calls
    requests_mock.post(
        f"{mock_client.BASE_URL}/order/newtradeorder",
        json={"StatusReason": "1", "OrderId": 12345},
        status_code=200
    )

    result = mock_client.close_all_trades(tolerance=0.05)
    assert len(result) == 2, "Should have results for each position."
    assert all("OrderId" in r for r in result), "Each response should contain an OrderId."


def test_close_all_trades_new_no_positions(mock_client, requests_mock):
    """
    Test close_all_trades_new with an empty list of positions.
    """
    result = mock_client.close_all_trades_new(open_positions=[], tolerance=0.1)
    assert result == [], "Empty open_positions should return empty list"


def test_get_trade_history_success(mock_client, requests_mock):
    """
    Test get_trade_history returns a DataFrame when successful.
    """
    mock_data = {
        "TradeHistory": [
            {"TradeId": 101, "MarketId": 999, "Profit": 10.0},
            {"TradeId": 102, "MarketId": 888, "Profit": -5.0},
        ]
    }
    requests_mock.get(
        f"{mock_client.BASE_URL}/order/tradehistory",
        json=mock_data,
        status_code=200
    )

    df = mock_client.get_trade_history(from_ts="2020-01-01", max_results=2)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert "TradeId" in df.columns


def test_get_trade_history_failure(mock_client, requests_mock):
    """
    Test that an exception is raised if trade history retrieval fails.
    """
    requests_mock.get(
        f"{mock_client.BASE_URL}/order/tradehistory",
        text="Server error",
        status_code=500
    )

    with pytest.raises(Exception) as excinfo:
        mock_client.get_trade_history()
    assert "Failed to retrieve trade history" in str(excinfo.value)


def test_get_long_series(mock_client, requests_mock):
    """
    Test that get_long_series calls get_ohlc repeatedly and concatenates results.
    This is a simplified test: we just mock get_ohlc calls and confirm all data is merged.
    """
    # We'll mock the get_ohlc method, not the direct requests inside it,
    # because get_long_series loops over time intervals and calls get_ohlc.
    data_chunk_1 = pd.DataFrame({"Date": ["2024-01-01T00:00:00Z"], "Open": [1.1]})
    data_chunk_2 = pd.DataFrame({"Date": ["2024-01-01T01:00:00Z"], "Open": [1.2]})

    def mock_get_ohlc(*args, **kwargs):
        # Return a different DataFrame on each call
        if not hasattr(mock_get_ohlc, "call_count"):
            mock_get_ohlc.call_count = 0
        mock_get_ohlc.call_count += 1
        if mock_get_ohlc.call_count == 1:
            return data_chunk_1
        else:
            return data_chunk_2

    # Monkeypatch the method on mock_client
    mock_client.get_ohlc = mock_get_ohlc

    df = mock_client.get_long_series(
        market_id="123",
        n_months=1,
        by_time='1D',  # Just an example
        n=2,
        interval="HOUR",
        span=1
    )

    # We expect the result to contain both rows
    assert len(df) == 2, "Should concatenate both data chunks."
    assert round(df["Open"].iloc[0], 1) == 1.1
    assert round(df["Open"].iloc[1], 1) == 1.2
