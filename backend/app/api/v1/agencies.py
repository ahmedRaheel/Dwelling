"""Public real estate agency directory, opt-in contact information only."""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from app.api.deps import DB, CurrentUser, require_roles
from app.models.entities import ListingStatus, Property, Role, Tenant, User
from app.schemas.domain import AgencyResponse, AgencyUpdate

router = APIRouter(prefix='/agencies', tags=['Agencies'])


def response(tenant: Tenant, count: int) -> AgencyResponse:
    return AgencyResponse(id=tenant.id, name=tenant.name, slug=tenant.slug,
                          public_description=tenant.public_description,
                          public_city=tenant.public_city, public_phone=tenant.public_phone,
                          public_email=tenant.public_email, published_listings=count)


@router.get('', response_model=list[AgencyResponse])
async def agency_directory(db: DB, city: Annotated[str | None, Query(max_length=100)] = None):
    query = (select(Tenant, func.count(Property.id).label('inventory'))
             .outerjoin(Property, (Property.tenant_id == Tenant.id) &
                        (Property.status == ListingStatus.published))
             .where(Tenant.active.is_(True)).group_by(Tenant.id)
             .order_by(func.count(Property.id).desc(), Tenant.name.asc()).limit(100))
    if city:
        query = query.where(Tenant.public_city.ilike(f'%{city.strip()}%'))
    rows = (await db.execute(query)).all()
    return [response(agency, count) for agency, count in rows]


@router.get('/me', response_model=AgencyResponse)
async def my_agency(db: DB, user: CurrentUser):
    if user.role not in (Role.owner, Role.admin, Role.broker):
        raise HTTPException(403, 'Agency account required')
    tenant = await db.scalar(select(Tenant).where(Tenant.id == user.tenant_id))
    if tenant is None:
        raise HTTPException(404, 'Agency not found')
    count = await db.scalar(select(func.count(Property.id)).where(
        Property.tenant_id == tenant.id, Property.status == ListingStatus.published)) or 0
    return response(tenant, count)


@router.patch('/me', response_model=AgencyResponse)
async def update_agency(payload: AgencyUpdate, db: DB,
                        user: Annotated[User, Depends(require_roles(Role.owner, Role.admin))]):
    tenant = await db.scalar(select(Tenant).where(Tenant.id == user.tenant_id))
    if tenant is None:
        raise HTTPException(404, 'Agency not found')
    for field, value in payload.model_dump(mode='json').items():
        setattr(tenant, field, value)
    await db.flush()
    count = await db.scalar(select(func.count(Property.id)).where(
        Property.tenant_id == tenant.id, Property.status == ListingStatus.published)) or 0
    return response(tenant, count)


@router.get('/{slug}', response_model=AgencyResponse)
async def agency_profile(slug: str, db: DB):
    tenant = await db.scalar(select(Tenant).where(Tenant.slug == slug, Tenant.active.is_(True)))
    if tenant is None:
        raise HTTPException(404, 'Agency not found')
    count = await db.scalar(select(func.count(Property.id)).where(
        Property.tenant_id == tenant.id, Property.status == ListingStatus.published)) or 0
    return response(tenant, count)
