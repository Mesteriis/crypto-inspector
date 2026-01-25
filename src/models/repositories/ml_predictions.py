"""Repository for ML prediction database operations."""

import json
import logging
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.ml_predictions import MLModelPerformance, MLPredictionRecord
from service.ml.models import ForecastResult

logger = logging.getLogger(__name__)


class MLPredictionRepository:
    """Repository for ML prediction CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_prediction(
        self,
        symbol: str,
        interval: str,
        model_name: str,
        forecast: ForecastResult,
        context_prices: list[float],
        prediction_timestamp: int,
        prediction_horizon: int,
    ) -> MLPredictionRecord:
        """
        Save ML prediction to database.

        Args:
            symbol: Trading pair symbol
            interval: Time interval
            model_name: ML model name
            forecast: Forecast result
            context_prices: Historical prices used for prediction
            prediction_timestamp: When prediction was made
            prediction_horizon: How many candles ahead predicted

        Returns:
            Saved MLPredictionRecord
        """
        # Get the final predicted price (last in horizon)
        predicted_price = forecast.predictions[-1] if forecast.predictions else 0

        record = MLPredictionRecord(
            symbol=symbol,
            interval=interval,
            model_name=model_name,
            prediction_timestamp=prediction_timestamp,
            prediction_horizon=prediction_horizon,
            predicted_price=Decimal(str(predicted_price)),
            context_prices=json.dumps(context_prices),
            confidence_percentage=forecast.confidence_pct,
            confidence_low=Decimal(str(forecast.confidence_low[-1])) if forecast.confidence_low else None,
            confidence_high=Decimal(str(forecast.confidence_high[-1])) if forecast.confidence_high else None,
            direction_prediction=forecast.direction,
        )

        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)

        logger.info(
            f"Saved prediction: {symbol} {interval} {model_name} "
            f"predicted {predicted_price} at {datetime.fromtimestamp(prediction_timestamp / 1000)}"
        )

        return record

    async def update_actual_price(
        self,
        prediction_id: int,
        actual_price: float,
        actual_timestamp: int,
    ) -> MLPredictionRecord:
        """
        Update prediction with actual realized price.

        Args:
            prediction_id: ID of prediction record
            actual_price: Actual realized price
            actual_timestamp: When actual price was recorded

        Returns:
            Updated MLPredictionRecord
        """
        stmt = select(MLPredictionRecord).where(MLPredictionRecord.id == prediction_id)
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()

        if not record:
            raise ValueError(f"Prediction record {prediction_id} not found")

        # Update actual values
        record.actual_price = Decimal(str(actual_price))
        record.actual_timestamp = actual_timestamp

        # Calculate errors
        if record.predicted_price and record.actual_price:
            record.absolute_error = abs(record.actual_price - record.predicted_price)
            if record.actual_price != 0:
                record.percentage_error = (record.actual_price - record.predicted_price) / record.actual_price * 100

        # Determine direction accuracy
        if record.context_prices and record.actual_price:
            try:
                context_prices = json.loads(record.context_prices)
                if context_prices:
                    last_context_price = Decimal(str(context_prices[-1]))
                    predicted_direction = record.predicted_price > last_context_price
                    actual_direction = record.actual_price > last_context_price
                    record.direction_correct = predicted_direction == actual_direction
            except (json.JSONDecodeError, IndexError):
                record.direction_correct = None

        await self.session.commit()
        await self.session.refresh(record)

        logger.info(
            f"Updated prediction {prediction_id}: actual {actual_price}, "
            f"error {record.absolute_error}, direction_correct {record.direction_correct}"
        )

        return record

    async def get_unresolved_predictions(
        self,
        symbol: str | None = None,
        model_name: str | None = None,
        limit: int = 1000,
    ) -> list[MLPredictionRecord]:
        """
        Get predictions that don't have actual prices yet.

        Args:
            symbol: Filter by symbol (optional)
            model_name: Filter by model (optional)
            limit: Maximum records to return

        Returns:
            List of unresolved predictions
        """
        stmt = select(MLPredictionRecord).where(MLPredictionRecord.actual_price.is_(None))

        if symbol:
            stmt = stmt.where(MLPredictionRecord.symbol == symbol)
        if model_name:
            stmt = stmt.where(MLPredictionRecord.model_name == model_name)

        stmt = stmt.order_by(MLPredictionRecord.prediction_timestamp.desc()).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_predictions_for_backtesting(
        self,
        symbol: str,
        interval: str,
        model_name: str,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int = 10000,
    ) -> list[MLPredictionRecord]:
        """
        Get predictions with actual results for backtesting analysis.

        Args:
            symbol: Trading pair symbol
            interval: Time interval
            model_name: ML model name
            start_time: Start timestamp filter (optional)
            end_time: End timestamp filter (optional)
            limit: Maximum records to return

        Returns:
            List of predictions with actual results
        """
        stmt = select(MLPredictionRecord).where(
            MLPredictionRecord.symbol == symbol,
            MLPredictionRecord.interval == interval,
            MLPredictionRecord.model_name == model_name,
            MLPredictionRecord.actual_price.isnot(None),
        )

        if start_time:
            stmt = stmt.where(MLPredictionRecord.prediction_timestamp >= start_time)
        if end_time:
            stmt = stmt.where(MLPredictionRecord.prediction_timestamp <= end_time)

        stmt = stmt.order_by(MLPredictionRecord.prediction_timestamp.desc()).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def calculate_model_performance(
        self,
        symbol: str,
        interval: str,
        model_name: str,
    ) -> MLModelPerformance:
        """
        Calculate and update performance statistics for a model.

        Args:
            symbol: Trading pair symbol
            interval: Time interval
            model_name: ML model name

        Returns:
            Updated MLModelPerformance record
        """
        # Get all evaluated predictions
        predictions = await self.get_predictions_for_backtesting(
            symbol=symbol,
            interval=interval,
            model_name=model_name,
        )

        if not predictions:
            logger.warning(f"No evaluated predictions for {symbol} {interval} {model_name}")
            return None

        # Calculate metrics
        total_predictions = len(predictions)
        evaluated_predictions = len([p for p in predictions if p.actual_price is not None])

        if evaluated_predictions == 0:
            logger.warning("No evaluated predictions with actual prices")
            return None

        # Error calculations
        absolute_errors = [float(p.absolute_error) for p in predictions if p.absolute_error is not None]
        percentage_errors = [float(p.percentage_error) for p in predictions if p.percentage_error is not None]
        direction_correct = [p.direction_correct for p in predictions if p.direction_correct is not None]

        mean_absolute_error = Decimal(str(sum(absolute_errors) / len(absolute_errors))) if absolute_errors else None
        (Decimal(str(sum(percentage_errors) / len(percentage_errors))) if percentage_errors else None)
        direction_accuracy = (
            Decimal(str(sum(direction_correct) / len(direction_correct) * 100)) if direction_correct else None
        )

        # RMSE calculation
        squared_errors = [e**2 for e in absolute_errors]
        rmse = Decimal(str((sum(squared_errors) / len(squared_errors)) ** 0.5)) if squared_errors else None

        # MAPE calculation (avoid division by zero)
        abs_percentage_errors = [abs(e) for e in percentage_errors]
        mape = Decimal(str(sum(abs_percentage_errors) / len(abs_percentage_errors))) if abs_percentage_errors else None

        # Confidence statistics
        confidences = [p.confidence_percentage for p in predictions if p.confidence_percentage is not None]
        avg_confidence = Decimal(str(sum(confidences) / len(confidences))) if confidences else None

        # Calculate confidence coefficient (0-1 scale)
        # Based on accuracy, direction accuracy, and error magnitude
        if mean_absolute_error and direction_accuracy:
            # Normalize MAE (assuming typical crypto price ranges)
            normalized_mae = float(mean_absolute_error) / 1000  # Adjust based on typical price scales
            error_score = 1 / (1 + normalized_mae)
            accuracy_score = float(direction_accuracy) / 100
            confidence_coefficient = Decimal(str(0.7 * error_score + 0.3 * accuracy_score))
        else:
            confidence_coefficient = None

        # Get timing information
        first_pred = min(predictions, key=lambda p: p.prediction_timestamp)
        last_pred = max(predictions, key=lambda p: p.prediction_timestamp)

        # Upsert performance record
        stmt = select(MLModelPerformance).where(
            MLModelPerformance.symbol == symbol,
            MLModelPerformance.model_name == model_name,
            MLModelPerformance.interval == interval,
        )

        result = await self.session.execute(stmt)
        performance_record = result.scalar_one_or_none()

        if performance_record is None:
            performance_record = MLModelPerformance(
                symbol=symbol,
                model_name=model_name,
                interval=interval,
            )
            self.session.add(performance_record)

        # Update all fields
        performance_record.total_predictions = total_predictions
        performance_record.evaluated_predictions = evaluated_predictions
        performance_record.mean_absolute_error = mean_absolute_error
        performance_record.root_mean_square_error = rmse
        performance_record.mean_absolute_percentage_error = mape
        performance_record.direction_accuracy = direction_accuracy
        performance_record.average_confidence = avg_confidence
        performance_record.confidence_coefficient = confidence_coefficient
        performance_record.first_prediction_at = datetime.fromtimestamp(first_pred.prediction_timestamp / 1000, tz=UTC)
        performance_record.last_prediction_at = datetime.fromtimestamp(last_pred.prediction_timestamp / 1000, tz=UTC)
        performance_record.last_evaluation_at = datetime.now(UTC)

        await self.session.commit()
        await self.session.refresh(performance_record)

        logger.info(
            f"Updated performance for {symbol} {interval} {model_name}: "
            f"MAE={mean_absolute_error}, Direction Acc={direction_accuracy}%, "
            f"Confidence Coeff={confidence_coefficient}"
        )

        return performance_record

    async def get_model_rankings(
        self,
        symbol: str,
        interval: str,
    ) -> list[dict]:
        """
        Get ranked list of models by performance for a symbol/interval.

        Args:
            symbol: Trading pair symbol
            interval: Time interval

        Returns:
            List of model performance dictionaries sorted by confidence coefficient
        """
        stmt = (
            select(MLModelPerformance)
            .where(
                MLModelPerformance.symbol == symbol,
                MLModelPerformance.interval == interval,
                MLModelPerformance.confidence_coefficient.isnot(None),
            )
            .order_by(MLModelPerformance.confidence_coefficient.desc())
        )

        result = await self.session.execute(stmt)
        performances = result.scalars().all()

        return [
            {
                "model_name": perf.model_name,
                "confidence_coefficient": float(perf.confidence_coefficient),
                "mean_absolute_error": float(perf.mean_absolute_error) if perf.mean_absolute_error else None,
                "direction_accuracy": float(perf.direction_accuracy) if perf.direction_accuracy else None,
                "evaluated_predictions": perf.evaluated_predictions,
                "last_evaluation": perf.last_evaluation_at.isoformat() if perf.last_evaluation_at else None,
            }
            for perf in performances
        ]

    async def get_prediction_history(
        self,
        symbol: str,
        interval: str,
        model_name: str,
        days: int = 30,
    ) -> list[MLPredictionRecord]:
        """
        Get recent prediction history for visualization.

        Args:
            symbol: Trading pair symbol
            interval: Time interval
            model_name: ML model name
            days: How many days of history to retrieve

        Returns:
            List of recent predictions with actual results
        """
        cutoff_time = int((datetime.now(UTC).timestamp() - days * 86400) * 1000)

        stmt = (
            select(MLPredictionRecord)
            .where(
                MLPredictionRecord.symbol == symbol,
                MLPredictionRecord.interval == interval,
                MLPredictionRecord.model_name == model_name,
                MLPredictionRecord.prediction_timestamp >= cutoff_time,
            )
            .order_by(MLPredictionRecord.prediction_timestamp.desc())
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())
