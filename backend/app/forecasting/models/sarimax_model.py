"""SARIMAX-based forecasting model."""

import numpy as np
import pandas as pd

from app.forecasting.models.base import BaseForecastModel


class SARIMAXForecastModel(BaseForecastModel):
    """SARIMAX model for price forecasting.

    Statistical baseline model that captures seasonality and trend.
    Uses statsmodels SARIMAX implementation.
    """

    def __init__(self, **params):
        defaults = {
            "order": (1, 1, 1),
            "seasonal_order": (1, 1, 1, 24),  # 24h seasonality for hourly data
        }
        defaults.update(params)
        super().__init__(name="sarimax", **defaults)
        self.model = None
        self.results = None

    def train(self, X: pd.DataFrame, y: pd.Series) -> dict:
        """Train the SARIMAX model.

        Note: SARIMAX uses exogenous variables (X) differently from tree models.
        X columns are treated as exogenous regressors.
        """
        try:
            from statsmodels.tsa.statespace.sarimax import SARIMAX
        except ImportError:
            raise ImportError("statsmodels is required: pip install statsmodels")

        exog = X if not X.empty else None
        self.model = SARIMAX(
            y,
            exog=exog,
            order=self.params["order"],
            seasonal_order=self.params["seasonal_order"],
            enforce_stationarity=False,
            enforce_invertibility=False,
        )
        self.results = self.model.fit(disp=False)
        self.is_trained = True

        # In-sample metrics
        y_pred = self.results.fittedvalues.values
        return self.compute_metrics(y, y_pred)

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Generate predictions using trained SARIMAX model."""
        if not self.is_trained or self.results is None:
            raise RuntimeError("Model must be trained before prediction")
        n_steps = len(X)
        exog = X if not X.empty else None
        forecast = self.results.forecast(steps=n_steps, exog=exog)
        return forecast.values

    def predict_intervals(
        self, X: pd.DataFrame, confidence: float = 0.9
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Generate predictions with confidence intervals from SARIMAX."""
        if not self.is_trained or self.results is None:
            raise RuntimeError("Model must be trained before prediction")
        n_steps = len(X)
        exog = X if not X.empty else None
        forecast = self.results.get_forecast(steps=n_steps, exog=exog, alpha=1 - confidence)
        pred = forecast.predicted_mean.values
        ci = forecast.conf_int()
        return pred, ci.iloc[:, 0].values, ci.iloc[:, 1].values
