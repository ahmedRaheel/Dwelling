"""Holdout-evaluated asking-price model; never fabricate predictions for cold-start markets."""
import asyncio
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.models.entities import ListingStatus, Property, Purpose
from app.schemas.domain import PredictionFeatures, PredictionResult

CATEGORICAL = ['kind', 'city', 'area_name']
NUMERIC = ['area_sqft', 'bedrooms', 'bathrooms', 'furnished']
COLUMNS = CATEGORICAL + NUMERIC
_cache: dict[str, tuple[tuple[int, str], Pipeline, float, int]] = {}
_train_lock = asyncio.Lock()


def features_from_property(item: Property) -> PredictionFeatures:
    return PredictionFeatures(purpose=item.purpose, kind=item.kind, city=item.city,
                              area_name=item.area_name, area_sqft=float(item.area_sqft),
                              bedrooms=item.bedrooms, bathrooms=item.bathrooms, furnished=item.furnished)


def row_from_property(item: Property) -> dict:
    return {'kind': item.kind.value, 'city': item.city.lower(), 'area_name': item.area_name.lower(),
            'area_sqft': float(item.area_sqft), 'bedrooms': item.bedrooms,
            'bathrooms': item.bathrooms, 'furnished': int(item.furnished), 'price': float(item.price)}


def _fit(rows: list[dict]) -> tuple[Pipeline, float]:
    frame = pd.DataFrame(rows)
    x = frame[COLUMNS]
    y = np.log1p(frame['price'].to_numpy())
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42)
    preprocessor = ColumnTransformer([
        ('categorical', Pipeline([('impute', SimpleImputer(strategy='most_frequent')),
                                   ('onehot', OneHotEncoder(handle_unknown='ignore'))]), CATEGORICAL),
        ('numerical', Pipeline([('impute', SimpleImputer(strategy='median'))]), NUMERIC),
    ])
    pipeline = Pipeline([('preprocess', preprocessor),
                         ('regressor', RandomForestRegressor(n_estimators=100, min_samples_leaf=2,
                                                             random_state=42, n_jobs=1))])
    pipeline.fit(x_train, y_train)
    estimates = np.expm1(pipeline.predict(x_test))
    mae = mean_absolute_error(np.expm1(y_test), estimates)
    # Train a final model on all observations after holdout evaluation.
    pipeline.fit(x, y)
    return pipeline, float(mae)


async def predict(db: AsyncSession, features: PredictionFeatures, exclude_property_id=None) -> PredictionResult:
    cfg = get_settings()
    listings = (await db.scalars(select(Property).where(
        Property.status == ListingStatus.published,
        Property.purpose == features.purpose,
        Property.currency == 'PKR',
        Property.price > 0,
    ))).all()
    # Protect against mixing commercial land and PG per-bed rates in one estimate.
    matches = [item for item in listings if item.kind == features.kind and item.id != exclude_property_id]
    if len(matches) < cfg.min_training_samples:
        return PredictionResult(status='insufficient_data',
                                reason=f'At least {cfg.min_training_samples} published comparable {features.kind.value} asking prices are required.',
                                sample_count=len(matches))
    rows = [row_from_property(item) for item in matches]
    signature = (len(matches), str(max(item.updated_at for item in matches)))
    key = f'{features.purpose.value}:{features.kind.value}'
    async with _train_lock:
        cached = _cache.get(key)
        if cached is None or cached[0] != signature:
            pipeline, mae = await asyncio.to_thread(_fit, rows)
            _cache[key] = (signature, pipeline, mae, len(matches))
        _, pipeline, mae, count = _cache[key]
    data = {'kind': features.kind.value, 'city': features.city.lower(),
            'area_name': features.area_name.lower(), 'area_sqft': features.area_sqft,
            'bedrooms': features.bedrooms, 'bathrooms': features.bathrooms,
            'furnished': int(features.furnished)}
    estimate = await asyncio.to_thread(lambda: float(np.expm1(pipeline.predict(pd.DataFrame([data]))[0])))
    return PredictionResult(status='available', estimate=round(max(estimate, 0), 2),
                            method='random_forest_log_price', sample_count=count,
                            holdout_mae=round(mae, 2))
