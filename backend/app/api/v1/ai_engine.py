from typing import Annotated
from uuid import UUID
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from app.api.deps import DB, CurrentUser, OptionalUser, require_roles
from app.api.v1.listings import ensure_viewable, get_property
from app.models.entities import (AIPrediction, Interaction, ListingStatus, MarketTrend,
                                 PropertyKind, Purpose, Role, User)
from app.schemas.domain import (BrokerMatch, InteractionInput, PredictionFeatures, PredictionResult,
                                Recommendation, RentForecast, TrendResponse)
from app.services.pricing import features_from_property, predict
from app.services.recommendations import broker_matches, customer_recommendations

router = APIRouter(prefix='/ai', tags=['AI intelligence'])


@router.post('/predict', response_model=PredictionResult)
async def price_prediction(features: PredictionFeatures, db: DB, user: CurrentUser):
    return await predict(db, features)


@router.get('/valuation/{property_id}', response_model=PredictionResult)
async def listing_valuation(property_id: UUID, db: DB, user: OptionalUser):
    item = await get_property(db, property_id)
    ensure_viewable(user, item)
    if item.currency != 'PKR':
        return PredictionResult(status='insufficient_data', reason='Estimation currently supports PKR listings only')
    result = await predict(db, features_from_property(item), exclude_property_id=item.id)
    if user and result.status == 'available' and result.estimate:
        db.add(AIPrediction(tenant_id=user.tenant_id, user_id=user.id, property_id=item.id,
                            purpose=item.purpose, estimated_price=result.estimate,
                            algorithm=result.method or 'unknown', training_count=result.sample_count,
                            model_mae=result.holdout_mae))
        await db.flush()
    return result


@router.get('/recommendations', response_model=list[Recommendation])
async def recommend(db: DB, user: CurrentUser, limit: int = Query(12, ge=1, le=30)):
    return await customer_recommendations(db, user, limit)


@router.post('/interactions', status_code=201)
async def record_interaction(payload: InteractionInput, db: DB, user: CurrentUser):
    item = await get_property(db, payload.property_id)
    if item.status != ListingStatus.published:
        raise HTTPException(422, 'Only published listings can be interacted with')
    db.add(Interaction(tenant_id=user.tenant_id, user_id=user.id,
                       property_id=item.id, action=payload.action))
    await db.flush()
    return {'message': 'Interaction recorded'}


@router.get('/broker/matches', response_model=list[BrokerMatch])
async def match_leads(db: DB, user: Annotated[User, Depends(require_roles(Role.owner, Role.admin, Role.broker))]):
    return await broker_matches(db, user)


@router.get('/trends', response_model=list[TrendResponse])
async def market_trends(db: DB, user: OptionalUser, city: str = Query(..., min_length=2, max_length=100),
                        kind: PropertyKind | None = None, area_name: str | None = None):
    stmt = select(MarketTrend).where(MarketTrend.verified.is_(True), MarketTrend.city.ilike(city))
    if kind:
        stmt = stmt.where(MarketTrend.kind == kind)
    if area_name:
        stmt = stmt.where(MarketTrend.area_name.ilike(area_name))
    trends = (await db.scalars(stmt.order_by(MarketTrend.month.desc()).limit(24))).all()
    return [TrendResponse.model_validate(row, from_attributes=True) for row in trends]


@router.get('/rent-forecast/{property_id}', response_model=RentForecast)
async def rent_forecast(property_id: UUID, db: DB, user: OptionalUser,
                        months: int = Query(6, ge=1, le=12)):
    item = await get_property(db, property_id)
    ensure_viewable(user, item)
    if item.purpose != Purpose.rent or item.currency != 'PKR':
        raise HTTPException(422, 'Rent forecasts require a PKR rental listing')
    stmt = select(MarketTrend).where(MarketTrend.verified.is_(True),
                                     MarketTrend.city.ilike(item.city),
                                     MarketTrend.area_name.ilike(item.area_name),
                                     MarketTrend.kind == item.kind,
                                     MarketTrend.median_monthly_rent.is_not(None)).order_by(MarketTrend.month.desc()).limit(12)
    observations = list(reversed((await db.scalars(stmt)).all()))
    if len(observations) < 4:
        return RentForecast(status='insufficient_data', reason='At least four verified monthly rent benchmarks are required')
    values = np.array([float(record.median_monthly_rent) for record in observations])
    # Predict local trend percentage, anchored to known asking rent; cap extrapolation to avoid runaway forecasts.
    x = np.arange(len(values), dtype=float)
    slope = float(np.polyfit(x, np.log(values), 1)[0])
    slope = float(np.clip(slope, -0.03, 0.03))
    projected = []
    for step in range(1, months + 1):
        base = observations[-1].month
        shifted = base.year * 12 + base.month - 1 + step
        forecast_date = base.replace(year=shifted // 12, month=shifted % 12 + 1, day=1)
        projected.append({'month': forecast_date.strftime('%Y-%m'),
                          'estimated_monthly_rent': round(float(item.price) * float(np.exp(slope * step)), 2)})
    return RentForecast(status='available', projected=projected,
                        method='capped_log_linear_verified_area_trend')
