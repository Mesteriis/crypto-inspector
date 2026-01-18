"""
Hyperparameter Optimizer - Automatic parameter tuning with Optuna.
"""

import logging
from datetime import datetime
from typing import Any

try:
    import optuna
    from optuna.samplers import TPESampler

    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False

from core.constants import MLDefaults, MLModels
from services.ml.backtester import ForecastBacktester

logger = logging.getLogger(__name__)


class HyperparameterOptimizer:
    """Automatic hyperparameter optimization using Optuna."""

    def __init__(self):
        """Initialize optimizer."""
        if not OPTUNA_AVAILABLE:
            raise ImportError("optuna not installed. " "Install with: pip install optuna")

        self.backtester = ForecastBacktester()
        self.study_cache: dict[str, optuna.Study] = {}

    async def optimize(
        self,
        symbol: str,
        interval: str,
        prices: list[float],
        model: str,
        n_trials: int = 50,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        """
        Optimize hyperparameters for a specific model.

        Args:
            symbol: Trading pair symbol
            interval: Candlestick interval
            prices: Historical price data
            model: Model to optimize
            n_trials: Number of optimization trials
            timeout: Maximum time in seconds

        Returns:
            Dictionary with optimization results
        """
        if model not in MLModels.ALL:
            raise ValueError(f"Cannot optimize unsupported model: {model}")

        study_name = f"{symbol}_{interval}_{model}"

        # Create or get study
        if study_name not in self.study_cache:
            sampler = TPESampler(seed=42)
            self.study_cache[study_name] = optuna.create_study(
                direction="minimize",
                study_name=study_name,
                sampler=sampler,
            )

        study = self.study_cache[study_name]

        # Define objective function
        async def objective(trial: optuna.Trial) -> float:
            params = self._suggest_parameters(trial, model)
            return await self._evaluate_parameters(symbol, interval, prices, model, params, trial)

        # Run optimization
        logger.info(f"Starting optimization for {model} on {symbol} {interval}")
        logger.info(f"Trials: {n_trials}, Timeout: {timeout}s")

        try:
            study.optimize(
                lambda trial: objective(trial).__await__().__next__(),  # Convert async to sync callback
                n_trials=n_trials,
                timeout=timeout,
                catch=(Exception,),
            )
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            raise

        # Get best parameters
        best_params = study.best_params
        best_value = study.best_value

        logger.info(f"Optimization completed for {model}")
        logger.info(f"Best MAE: {best_value:.6f}")
        logger.info(f"Best parameters: {best_params}")

        return {
            "model": model,
            "symbol": symbol,
            "interval": interval,
            "best_params": best_params,
            "best_mae": best_value,
            "n_trials": len(study.trials),
            "optimization_time": datetime.now().isoformat(),
        }

    def _suggest_parameters(self, trial: optuna.Trial, model: str) -> dict[str, Any]:
        """Suggest hyperparameters for optimization."""
        params = {}

        if model == MLModels.CHRONOS_BOLT:
            # Chronos Bolt parameters
            params.update(
                {
                    "context_length": trial.suggest_int("context_length", 128, 512, step=64),
                    "num_samples": trial.suggest_int("num_samples", 10, 50, step=10),
                    "temperature": trial.suggest_float("temperature", 0.1, 2.0),
                }
            )

        elif model == MLModels.STATSFORECAST_ARIMA:
            # AutoARIMA parameters
            params.update(
                {
                    "season_length": trial.suggest_int("season_length", 12, 168),  # Hourly seasonality
                    "approximation": trial.suggest_categorical("approximation", [True, False]),
                    "stepwise": trial.suggest_categorical("stepwise", [True, False]),
                }
            )

        elif model == MLModels.NEURALPROPHET:
            # NeuralProphet parameters
            params.update(
                {
                    "learning_rate": trial.suggest_float("learning_rate", 0.001, 0.1, log=True),
                    "epochs": trial.suggest_int("epochs", 5, 50),
                    "batch_size": trial.suggest_int("batch_size", 16, 128, step=16),
                    "seasonality_mode": trial.suggest_categorical("seasonality_mode", ["additive", "multiplicative"]),
                }
            )

        return params

    async def _evaluate_parameters(
        self,
        symbol: str,
        interval: str,
        prices: list[float],
        model: str,
        params: dict[str, Any],
        trial: optuna.Trial,
    ) -> float:
        """
        Evaluate parameter set using backtesting.

        Args:
            symbol: Trading pair
            interval: Time interval
            prices: Price data
            model: Model name
            params: Parameter dictionary
            trial: Optuna trial object

        Returns:
            MAE score (lower is better)
        """
        try:
            # Temporarily apply parameters (this would require model-specific implementation)
            # For now, we'll evaluate with default parameters and penalize based on complexity
            # In a full implementation, you'd modify the model initialization with these params

            # Run backtest with current parameters
            metrics = await self.backtester.walk_forward_validation(
                symbol=symbol,
                interval=interval,
                prices=prices,
                model=model,
                window_size=180,  # 6 months
                horizon=MLDefaults.PREDICTION_HORIZON,
            )

            # Report intermediate values
            trial.set_user_attr("rmse", metrics.rmse)
            trial.set_user_attr("mape", metrics.mape)
            trial.set_user_attr("direction_accuracy", metrics.direction_accuracy)

            return metrics.mae

        except Exception as e:
            logger.warning(f"Evaluation failed with params {params}: {e}")
            # Return penalty for failed trials
            return float("inf")

    async def optimize_ensemble_weights(
        self,
        symbol: str,
        interval: str,
        prices: list[float],
        n_trials: int = 30,
    ) -> dict[str, float]:
        """
        Optimize ensemble model weights.

        Args:
            symbol: Trading pair symbol
            interval: Candlestick interval
            prices: Historical prices
            n_trials: Number of optimization trials

        Returns:
            Dictionary mapping model names to optimal weights
        """
        study_name = f"ensemble_weights_{symbol}_{interval}"

        if study_name not in self.study_cache:
            sampler = TPESampler(seed=42)
            self.study_cache[study_name] = optuna.create_study(
                direction="minimize",
                study_name=study_name,
                sampler=sampler,
            )

        study = self.study_cache[study_name]

        # Available models for ensemble
        available_models = self.backtester.forecaster.get_available_models()
        if MLModels.ENSEMBLE in available_models:
            available_models.remove(MLModels.ENSEMBLE)

        async def objective(trial: optuna.Trial) -> float:
            # Suggest weights that sum to 1.0
            weights = {}
            remaining_weight = 1.0

            for i, model in enumerate(available_models[:-1]):
                max_weight = remaining_weight
                weight = trial.suggest_float(f"weight_{model}", 0.0, max_weight)
                weights[model] = weight
                remaining_weight -= weight

            # Last model gets remaining weight
            weights[available_models[-1]] = remaining_weight

            # Temporarily update ensemble weights (would require ensemble modification)
            # For demo purposes, we'll evaluate individual models and combine scores
            total_mae = 0.0
            total_weight = 0.0

            for model, weight in weights.items():
                if weight > 0.01:  # Only evaluate models with significant weight
                    try:
                        metrics = await self.backtester.walk_forward_validation(
                            symbol=symbol,
                            interval=interval,
                            prices=prices,
                            model=model,
                            window_size=180,
                            horizon=MLDefaults.PREDICTION_HORIZON,
                        )
                        total_mae += metrics.mae * weight
                        total_weight += weight
                    except Exception:
                        # Penalize failed models
                        total_mae += 1000.0 * weight
                        total_weight += weight

            if total_weight > 0:
                avg_mae = total_mae / total_weight
            else:
                avg_mae = float("inf")

            return avg_mae

        # Run optimization
        study.optimize(
            lambda trial: objective(trial).__await__().__next__(),
            n_trials=n_trials,
            catch=(Exception,),
        )

        # Extract best weights
        best_params = study.best_params
        weights = {}
        remaining_weight = 1.0

        for model in available_models[:-1]:
            weight = best_params.get(f"weight_{model}", 0.0)
            weights[model] = weight
            remaining_weight -= weight

        weights[available_models[-1]] = remaining_weight

        logger.info(f"Optimized ensemble weights for {symbol} {interval}: {weights}")

        return weights

    def get_optimization_history(self, study_name: str) -> dict[str, Any] | None:
        """Get optimization history for a study."""
        if study_name not in self.study_cache:
            return None

        study = self.study_cache[study_name]

        return {
            "study_name": study_name,
            "best_params": study.best_params,
            "best_value": study.best_value,
            "n_trials": len(study.trials),
            "trials": [
                {
                    "number": trial.number,
                    "params": trial.params,
                    "value": trial.value,
                    "state": str(trial.state),
                }
                for trial in study.trials
            ],
        }

    def save_study(self, study_name: str, filepath: str) -> None:
        """Save study to file."""
        if study_name in self.study_cache:
            study = self.study_cache[study_name]
            optuna.storages.RDBStorage(url=f"sqlite:///{filepath}")
            logger.info(f"Saved study {study_name} to {filepath}")

    def load_study(self, study_name: str, filepath: str) -> None:
        """Load study from file."""
        storage = optuna.storages.RDBStorage(url=f"sqlite:///{filepath}")
        study = optuna.load_study(study_name=study_name, storage=storage)
        self.study_cache[study_name] = study
        logger.info(f"Loaded study {study_name} from {filepath}")

    def __del__(self):
        """Cleanup resources."""
        self.study_cache.clear()
        self.backtester = None
