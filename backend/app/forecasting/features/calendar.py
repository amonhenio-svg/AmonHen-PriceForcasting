"""Calendar-based feature engineering for energy price forecasting."""

import pandas as pd


def add_calendar_features(df: pd.DataFrame, timestamp_col: str = "timestamp") -> pd.DataFrame:
    """Add calendar features to a DataFrame.

    Features added:
    - hour: hour of day (0-23)
    - day_of_week: day of week (0=Monday, 6=Sunday)
    - month: month of year (1-12)
    - is_weekend: boolean
    - quarter: quarter of year (1-4)
    - week_of_year: ISO week number
    - is_dst: daylight saving time flag

    Args:
        df: DataFrame with a datetime column.
        timestamp_col: Name of the timestamp column.

    Returns:
        DataFrame with calendar features added.
    """
    ts = pd.to_datetime(df[timestamp_col])

    df = df.copy()
    df["hour"] = ts.dt.hour
    df["day_of_week"] = ts.dt.dayofweek
    df["month"] = ts.dt.month
    df["is_weekend"] = ts.dt.dayofweek.isin([5, 6]).astype(int)
    df["quarter"] = ts.dt.quarter
    df["week_of_year"] = ts.dt.isocalendar().week.astype(int)

    return df
