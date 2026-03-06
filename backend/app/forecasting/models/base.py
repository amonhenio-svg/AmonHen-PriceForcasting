"""Base class for all forecasting models."""

from abc import ABC, abstractmethod

import numpy as np
import pandas as pd


class BaseForecastModel(ABC):
    """Abstract base class for forecasting models.

    All forecasting models should inherit from this class and implement
    the train and predict methods.
    """

    def __init__(self, name: str, **params):
        self.name = name
        self.params = params
        self.is_trained = False

    @abstractmethod
    def train(self, X: pd.DataFrame, y: pd.Series) -> dict:
        """Train the model.

        Args:
            X: Feature matrix (rows = timestamps, columns = features).
            y: Target values.

        Returns:
            Dict with training metrics (e.g., in-sample MAE, RMSE).
        """

    @abstractmethod
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Generate point predictions.

        Args:
            X: Feature matrix for prediction period.

        Returns:
            Array of predicted values.
        """

    def predict_intervals(
        self, X: pd.DataFrame, confidence: float = 0.9
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Generate predictions with confidence intervals.

        Args:
            X: Feature matrix for prediction period.
            confidence: Confidence level (default 0.9 = 90%).

        Returns:
            Tuple of (predictions, lower_bounds, upper_bounds).
        """
        predictions = self.predict(X)
        # Default: no intervals, subclasses can override
        return predictions, predictions, predictions

    @staticmethod
    def compute_metrics(y_true: pd.Series, y_pred: np.ndarray) -> dict:
        """Compute standard forecasting metrics."""
        errors = y_true.values - y_pred
        return {
            "mae": float(np.mean(np.abs(errors))),
            "rmse": float(np.sqrt(np.mean(errors**2))),
            "mape": float(np.mean(np.abs(errors / (y_true.values + 1e-8))) * 100),
        }
