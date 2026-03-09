"""Ensemble methods for combining multiple forecasting models."""

import numpy as np
import pandas as pd

from app.forecasting.models.base import BaseForecastModel


class WeightedEnsemble:
    """Weighted average ensemble of multiple forecasting models.

    Combines predictions from multiple models using configurable weights.
    Weights can be set manually or optimized based on validation performance.
    """

    def __init__(self, models: list[BaseForecastModel], weights: list[float] | None = None):
        self.models = models
        if weights is None:
            # Equal weights by default
            self.weights = [1.0 / len(models)] * len(models)
        else:
            total = sum(weights)
            self.weights = [w / total for w in weights]

    def train_all(self, X: pd.DataFrame, y: pd.Series) -> list[dict]:
        """Train all models and return their metrics."""
        metrics = []
        for model in self.models:
            m = model.train(X, y)
            metrics.append({"model": model.name, **m})
        return metrics

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Generate weighted ensemble prediction."""
        predictions = np.array([model.predict(X) for model in self.models])
        return np.average(predictions, axis=0, weights=self.weights)

    def optimize_weights(
        self, X_val: pd.DataFrame, y_val: pd.Series
    ) -> list[float]:
        """Optimize ensemble weights using validation data.

        Uses a simple grid search over weight combinations to minimize MAE.
        """
        predictions = [model.predict(X_val) for model in self.models]
        n_models = len(self.models)

        best_mae = float("inf")
        best_weights = self.weights

        # Simple grid search (works well for 2-3 models)
        steps = 20
        if n_models == 2:
            for w1 in range(steps + 1):
                w = [w1 / steps, 1 - w1 / steps]
                combined = np.average(predictions, axis=0, weights=w)
                mae = np.mean(np.abs(y_val.values - combined))
                if mae < best_mae:
                    best_mae = mae
                    best_weights = w
        else:
            # For more models, use equal weights as starting point
            # TODO: implement more sophisticated optimization
            pass

        self.weights = best_weights
        return best_weights

    def predict_intervals(
        self, X: pd.DataFrame, confidence: float = 0.9
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Generate weighted ensemble prediction with confidence intervals.

        Combines intervals from individual models using the same weights.
        """
        all_preds = []
        all_lower = []
        all_upper = []

        for model in self.models:
            preds, lower, upper = model.predict_intervals(X, confidence)
            all_preds.append(preds)
            all_lower.append(lower)
            all_upper.append(upper)

        preds = np.average(all_preds, axis=0, weights=self.weights)
        lower = np.average(all_lower, axis=0, weights=self.weights)
        upper = np.average(all_upper, axis=0, weights=self.weights)

        return preds, lower, upper
