"""Lag-based feature engineering for time series forecasting."""

import pandas as pd


def add_lag_features(
    df: pd.DataFrame,
    value_col: str = "value",
    lags: list[int] | None = None,
) -> pd.DataFrame:
    """Add lagged value features to a DataFrame.

    Args:
        df: DataFrame sorted by timestamp.
        value_col: Name of the value column to lag.
        lags: List of lag periods (in rows). Defaults to common energy market lags.

    Returns:
        DataFrame with lag features added.
    """
    if lags is None:
        # Default lags for hourly energy data:
        # 1h, 2h, 3h (recent), 24h (same hour yesterday),
        # 48h (2 days ago), 168h (same hour last week)
        lags = [1, 2, 3, 24, 48, 168]

    df = df.copy()
    for lag in lags:
        df[f"{value_col}_lag_{lag}"] = df[value_col].shift(lag)

    return df


def add_rolling_features(
    df: pd.DataFrame,
    value_col: str = "value",
    windows: list[int] | None = None,
) -> pd.DataFrame:
    """Add rolling statistics as features.

    Args:
        df: DataFrame sorted by timestamp.
        value_col: Name of the value column.
        windows: List of rolling window sizes. Defaults to common windows.

    Returns:
        DataFrame with rolling features added.
    """
    if windows is None:
        windows = [24, 48, 168]  # 1 day, 2 days, 1 week (hourly data)

    df = df.copy()
    for w in windows:
        df[f"{value_col}_rolling_mean_{w}"] = df[value_col].rolling(w).mean()
        df[f"{value_col}_rolling_std_{w}"] = df[value_col].rolling(w).std()

    return df
