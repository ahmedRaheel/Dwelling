"""Saved searches, live match counts, comparison, and locality suggestions."""
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import delete, func, or_, select
from app.api.deps import DB, CurrentUser, OptionalUser
from app.api.v1.listings import get_property, ensure_viewable
from app.models.entities import ListingStatus, Property, SavedSearch
from app.schemas.domain import (PropertyResponse, PropertySearchFilters, SavedSearchCreate,
                                 SavedSearchMatches, SavedSearchResponse)
from app.services.discovery import property_search_conditions

router = APIRouter(prefix='/discovery', tags=['Property discovery'])


@router.get('/locations', response_model=list[str])
async def location_suggestions(db: DB, q: Annotated[str, Query(min_length=2, max_length=100)],
                               city: Annotated[str | None, Query(max_length=100)] = None):
    """Suggestions only from published listings; no made-up housing-society directory."""
    conditions = [Property.status == ListingStatus.published]
    if city:
        conditions.append(Property.city.ilike(f'%{city.strip()}%'))
    term = f'%{q.strip()}%'
    conditions.append(or_(Property.city.ilike(term), Property.society.ilike(term), Property.area_name.ilike(term)))
    rows = (await db.execute(select(Property.city, Property.society, Property.area_name)
                             .where(*conditions).distinct().limit(60))).all()
    results: list[str] = []
    for place_city, society, neighbourhood in rows:
        for label in (society, neighbourhood, place_city):
            name = (label or '').strip()
            if name and name.casefold().find(q.strip().casefold()) >= 0 and name not in results:
                results.append(name)
    return sorted(results, key=str.casefold)[:12]


@router.get('/compare', response_model=list[PropertyResponse])
async def compare_properties(db: DB, user: OptionalUser,
                             ids: Annotated[list[UUID], Query(min_length=2, max_length=4)]):
    if len(set(ids)) != len(ids):
        raise HTTPException(422, 'Choose distinct listings')
    rows = (await db.scalars(select(Property).where(Property.id.in_(ids)))).all()
    by_id = {item.id: item for item in rows}
    if any(identifier not in by_id for identifier in ids):
        raise HTTPException(404, 'One or more listings are no longer available')
    for identifier in ids:
        ensure_viewable(user, by_id[identifier])
    return [by_id[identifier] for identifier in ids]


@router.get('/saved-searches', response_model=list[SavedSearchResponse])
async def list_saved_searches(db: DB, user: CurrentUser):
    return (await db.scalars(select(SavedSearch).where(
        SavedSearch.tenant_id == user.tenant_id, SavedSearch.user_id == user.id
    ).order_by(SavedSearch.created_at.desc()).limit(50))).all()


@router.post('/saved-searches', response_model=SavedSearchResponse, status_code=201)
async def save_search(payload: SavedSearchCreate, db: DB, user: CurrentUser):
    count = await db.scalar(select(func.count(SavedSearch.id)).where(
        SavedSearch.tenant_id == user.tenant_id, SavedSearch.user_id == user.id
    ))
    if count >= 30:
        raise HTTPException(409, 'Maximum of 30 saved searches per account')
    record = SavedSearch(tenant_id=user.tenant_id, user_id=user.id, name=payload.name,
                         filters=payload.filters.model_dump(exclude_none=True, mode='json'),
                         alerts_enabled=payload.alerts_enabled)
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record


async def owned_search(db: DB, user: CurrentUser, search_id: UUID) -> SavedSearch:
    record = await db.scalar(select(SavedSearch).where(
        SavedSearch.id == search_id, SavedSearch.tenant_id == user.tenant_id,
        SavedSearch.user_id == user.id))
    if record is None:
        raise HTTPException(404, 'Saved search not found')
    return record


@router.get('/saved-searches/{search_id}/matches', response_model=SavedSearchMatches)
async def search_matches(search_id: UUID, db: DB, user: CurrentUser):
    record = await owned_search(db, user, search_id)
    filters = PropertySearchFilters.model_validate(record.filters)
    conditions = property_search_conditions(filters)
    recent_since = record.last_checked_at or record.created_at
    new_count = await db.scalar(select(func.count(Property.id)).where(
        *conditions, Property.created_at > recent_since)) or 0
    items = (await db.scalars(select(Property).where(*conditions)
                              .order_by(Property.created_at.desc()).limit(24))).all()
    return SavedSearchMatches(search=record, new_count=new_count, items=items)


@router.post('/saved-searches/{search_id}/check', response_model=SavedSearchResponse)
async def mark_search_checked(search_id: UUID, db: DB, user: CurrentUser):
    record = await owned_search(db, user, search_id)
    record.last_checked_at = datetime.now(timezone.utc)
    await db.flush()
    return record


@router.delete('/saved-searches/{search_id}', status_code=204)
async def delete_saved_search(search_id: UUID, db: DB, user: CurrentUser):
    record = await owned_search(db, user, search_id)
    await db.delete(record)
