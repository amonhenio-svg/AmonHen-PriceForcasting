"""XGBoost-based forecasting model."""

import numpy as np
import pandas as pd

from app.forecasting.models.base import BaseForecastModel


class XGBoostForecastModel(BaseForecastModel):
    """XGBoost gradient boosting model for price forecasting.

    Good default model that handles mixed feature types well and
    provides competitive accuracy on structured/tabular data.

    Produces real confidence intervals by training separate quantile
    regression models for the lower and upper bounds.
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
        self._model_lower = None
        self._model_upper = None
        self._X_train = None
        self._y_train = None

    def train(self, X: pd.DataFrame, y: pd.Series) -> dict:
        """Train the XGBoost model."""
        try:
            import xgboost as xgb
        except ImportError:
            raise ImportError("xgboost is required: pip install xgboost")

        self.model = xgb.XGBRegressor(**self.params)
        self.model.fit(X, y)
        self.is_trained = True

        # Store training data for quantile model training on demand
        self._X_train = X
        self._y_train = y

        # In-sample metrics
        y_pred = self.model.predict(X)
        return self.compute_metrics(y, y_pred)

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Generate predictions using trained XGBoost model."""
        if not self.is_trained or self.model is None:
            raise RuntimeError("Model must be trained before prediction")
        return self.model.predict(X)

    def predict_intervals(
        self, X: pd.DataFrame, confidence: float = 0.9
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Generate predictions with confidence intervals.

        Trains quantile regression models for the lower and upper bounds
        using the stored training data.
        """
        if not self.is_trained or self.model is None:
            raise RuntimeError("Model must be trained before prediction")

        predictions = self.model.predict(X)

        # Train quantile models if not yet done
        if self._model_lower is None and self._X_train is not None:
            try:
                import xgboost as xgb

                alpha = (1 - confidence) / 2
                quantile_params = {
                    k: v for k, v in self.params.items()
                    if k != "objective"
                }
                quantile_params["objective"] = "reg:quantileerror"

                self._model_lower = xgb.XGBRegressor(
                    **quantile_params, quantile_alpha=alpha,
                )
                self._model_lower.fit(self._X_train, self._y_train)

                self._model_upper = xgb.XGBRegressor(
                    **quantile_params, quantile_alpha=1 - alpha,
                )
                self._model_upper.fit(self._X_train, self._y_train)
            except Exception:
                # Fallback: use residual-based intervals
                residuals = self._y_train.values - self.model.predict(self._X_train)
                std = np.std(residuals)
                z = 1.645 if confidence == 0.9 else 1.96
                return predictions, predictions - z * std, predictions + z * std

        if self._model_lower is not None and self._model_upper is not None:
            lower = self._model_lower.predict(X)
            upper = self._model_upper.predict(X)
            return predictions, lower, upper

        return predictions, predictions, predictions

    def feature_importance(self) -> dict[str, float]:
        """Get feature importance scores."""
        if not self.is_trained or self.model is None:
            raise RuntimeError("Model must be trained first")
        importance = self.model.feature_importances_
        features = self.model.get_booster().feature_names
        return dict(zip(features, importance))
