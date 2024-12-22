# tests/test_utils.py

import pytest
from datetime import datetime, timedelta
import pandas as pd
import re

# Import the functions we want to test from utils.py
from src.pygcapi.utils import (
    get_instruction_status_description,
    get_instruction_status_reason_description,
    get_order_status_description,
    get_order_status_reason_description,
    get_order_action_type_description,
    extract_every_nth,
    convert_to_dataframe
)

@pytest.mark.parametrize("status_code, expected", [
    ("1", "Accepted"),
    ("2", "Red Card"),
    ("999", "Unknown status code"),  # Non-existent code
])
def test_get_instruction_status_description(status_code, expected):
    """
    Test that get_instruction_status_description returns the correct description
    for various instruction status codes, and returns 'Unknown status code' if
    the code is not found in the lookup table.
    """
    result = get_instruction_status_description(status_code)
    assert result == expected


@pytest.mark.parametrize("reason_code, expected", [
    ("1", "OK"),
    ("7", "Unexpected Error"),
    ("999", "Unknown reason code"),  # Non-existent code
])
def test_get_instruction_status_reason_description(reason_code, expected):
    """
    Test that get_instruction_status_reason_description returns the correct
    description for various instruction status reason codes, and returns
    'Unknown reason code' if the code is not found.
    """
    result = get_instruction_status_reason_description(reason_code)
    assert result == expected


@pytest.mark.parametrize("status_code, expected", [
    ("1", "Pending"),
    ("2", "Accepted"),
    ("999", "Unknown status code"),  # Non-existent code
])
def test_get_order_status_description(status_code, expected):
    """
    Test that get_order_status_description returns the correct description
    for various order status codes, and returns 'Unknown status code' if
    the code is not found.
    """
    result = get_order_status_description(status_code)
    assert result == expected


@pytest.mark.parametrize("reason_code, expected", [
    ("1", "OK"),
    ("150", "Trigger prices of orders in If Done link must be valid."),
    ("9999", "Unknown reason code"),  # Non-existent code
])
def test_get_order_status_reason_description(reason_code, expected):
    """
    Test that get_order_status_reason_description returns the correct description
    for various order status reason codes, and returns 'Unknown reason code' if
    the code is not found.
    """
    result = get_order_status_reason_description(reason_code)
    assert result == expected


@pytest.mark.parametrize("action_type_code, expected", [
    ("1", "Opening Order"),
    ("8", "Cancelled Order"),
    ("999", "Unknown action type code"),  # Non-existent code
])
def test_get_order_action_type_description(action_type_code, expected):
    """
    Test that get_order_action_type_description returns the correct description
    for various order action type codes, and returns 'Unknown action type code'
    if the code is not found.
    """
    result = get_order_action_type_description(action_type_code)
    assert result == expected


def test_extract_every_nth_default_args():
    """
    Test the extract_every_nth function using default arguments.
    We simply verify that it returns a list of tuples and that each tuple
    has start_utc <= end_utc.
    """
    intervals = extract_every_nth()
    assert isinstance(intervals, list), "Function should return a list."
    for interval in intervals:
        assert isinstance(interval, tuple), "Each interval should be a tuple."
        assert len(interval) == 2, "Each tuple should contain (start_utc, end_utc)."
        start_utc, end_utc = interval
        assert start_utc <= end_utc, "Start of interval should be <= end of interval."


def test_extract_every_nth_custom_args():
    """
    Test the extract_every_nth function with custom arguments.
    For example, we choose n_months=1, by_time='1D', n=2 to get intervals
    in daily steps. We'll then do a rough check on how many intervals we get.
    """
    intervals = extract_every_nth(n_months=1, by_time='1D', n=2)
    # We expect approximately ~30 days / 2 = ~15 intervals (plus/minus 1)
    assert 10 < len(intervals) < 30, (
        "Expected a reasonable number of intervals (~15) within the 1-month daily range."
    )
    # Check ordering
    for start_utc, end_utc in intervals:
        assert start_utc <= end_utc


def test_convert_to_dataframe():
    """
    Test the convert_to_dataframe function to ensure that it properly parses
    the '/Date(...)' timestamps and creates a well-structured DataFrame with
    the correct time conversions.
    """
    # Sample data matching the structure expected by convert_to_dataframe
    sample_data = [
        {"BarDate": "/Date(1732075200000)/", "Open": 1.2345, "Close": 1.2350, "Volume": 100},
        {"BarDate": "/Date(1732075260000)/", "Open": 1.2350, "Close": 1.2360, "Volume": 200},
    ]

    df = convert_to_dataframe(sample_data)

    # Ensure we have a DataFrame
    assert isinstance(df, pd.DataFrame), "Function should return a pandas DataFrame."
    
    # Check that the 'Date' column exists and the old 'BarDate' column is removed
    assert 'Date' in df.columns, "DataFrame should have 'Date' column."
    assert 'BarDate' not in df.columns, "DataFrame should not have 'BarDate' column anymore."

    # Check that data was parsed correctly
    # The test data is in milliseconds; 1732075200000 corresponds to a datetime far in the future.
    # We just confirm we get a valid datetime type in UTC.
    assert pd.api.types.is_datetime64tz_dtype(df['Date']), "Date column should be timezone-aware datetime."

    # Check length
    assert len(df) == 2, "DataFrame should have two rows."
    # Check that numeric columns remained numeric
    for col in ['Open', 'Close', 'Volume']:
        assert pd.api.types.is_numeric_dtype(df[col]), f"{col} column should be numeric."
