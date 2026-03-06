"""XGBoost-based forecasting model."""

import numpy as np
import pandas as pd

from app.forecasting.models.base import BaseForecastModel


class XGBoostForecastModel(BaseForecastModel):
    """XGBoost gradient boosting model for price forecasting.

    Good default model that handles mixed feature types well and
    provides competitive accuracy on structured/tabular data.
    """

    def __init__(self, **params):
        defaults = {
            "n_estimators": 500,
            "max_depth": 6,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "min_child_weight": 5,
            "objective": "reg:squarederror",
        }
        defaults.update(params)
        super().__init__(name="xgboost", **defaults)
        self.model = None

    def train(self, X: pd.DataFrame, y: pd.Series) -> dict:
        """Train the XGBoost model."""
        try:
            import xgboost as xgb
        except ImportError:
            raise ImportError("xgboost is required: pip install xgboost")

        self.model = xgb.XGBRegressor(**self.params)
        self.model.fit(X, y)
        self.is_trained = True

        # In-sample metrics
        y_pred = self.model.predict(X)
        return self.compute_metrics(y, y_pred)

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Generate predictions using trained XGBoost model."""
        if not self.is_trained or self.model is None:
            raise RuntimeError("Model must be trained before prediction")
        return self.model.predict(X)

    def feature_importance(self) -> dict[str, float]:
        """Get feature importance scores."""
        if not self.is_trained or self.model is None:
            raise RuntimeError("Model must be trained first")
        importance = self.model.feature_importances_
        features = self.model.get_booster().feature_names
        return dict(zip(features, importance))
