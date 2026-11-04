from typing import Annotated, Literal
from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import DB, CurrentUser, OptionalUser, Pagination, require_roles
from app.models.entities import (Interaction, InteractionKind, ListingStatus, PGDetails, PortionDetails, Property, PropertyKind, Purpose,
                                 Role, User, Tenant)
from app.schemas.domain import PropertyCreate, PropertyPage, PropertyResponse, PropertyUpdate
from app.services.embeddings import encode, property_text
from app.services.listing_insights import calculate_market_insights
from app.features.listings.commands import assign_details, load_listing_relations

router = APIRouter(prefix='/listings', tags=['Listings'])


async def get_property(db: AsyncSession, property_id: UUID, lock: bool = False) -> Property:
    query = select(Property).where(Property.id == property_id)
    if lock:
        query = query.with_for_update(of=Property)
    property_obj = await db.scalar(query)
    if property_obj is None:
        raise HTTPException(404, 'Listing not found')
    await load_listing_relations(db, property_obj)
    return property_obj


def enforce_editor(user: User, item: Property) -> None:
    if user.tenant_id != item.tenant_id or (user.role == Role.broker and item.created_by != user.id):
        raise HTTPException(403, 'Cannot change this listing')


def ensure_viewable(user: User | None, item: Property) -> None:
    if item.status == ListingStatus.published:
        return
    if (user is None or user.tenant_id != item.tenant_id or user.role == Role.customer
            or (user.role == Role.broker and item.created_by != user.id)):
        raise HTTPException(404, 'Listing not found')



def property_input_from_existing(item: Property) -> dict:
    return {
        'title': item.title, 'description': item.description, 'kind': item.kind,
        'purpose': item.purpose, 'status': item.status, 'city': item.city,
        'area_name': item.area_name, 'address': item.address, 'society': item.society,
        'block': item.block, 'price_negotiable': item.price_negotiable, 'ready_to_move': item.ready_to_move,
        'video_url': item.video_url, 'price': item.price,
        'currency': item.currency, 'area_sqft': item.area_sqft, 'bedrooms': item.bedrooms,
        'bathrooms': item.bathrooms, 'furnished': item.furnished, 'photo_url': item.photo_url,
        'amenities': item.amenities, 'highlights': item.highlights,
        'contact_phone': item.contact_phone, 'latitude': item.latitude, 'longitude': item.longitude,
        'pg': ({'room_type': item.pg.room_type, 'total_beds': item.pg.total_beds,
                'available_beds': item.pg.available_beds, 'food_included': item.pg.food_included,
                'rules': item.pg.rules} if item.pg else None),
        'portion': ({'portion_kind': item.portion.portion_kind, 'floor_number': item.portion.floor_number,
                     'separate_electricity_meter': item.portion.separate_electricity_meter,
                     'separate_gas_meter': item.portion.separate_gas_meter,
                     'separate_water_meter': item.portion.separate_water_meter,
                     'parent_property_id': item.portion.parent_property_id} if item.portion else None),
    }


@router.get('', response_model=PropertyPage)
async def list_properties(db: DB, user: OptionalUser,
                          pagination: Annotated[Pagination, Depends()],
                          city: str | None = None,
                          agency_slug: str | None = Query(None, max_length=80),
                          society: str | None = Query(None, max_length=120),
                          block: str | None = Query(None, max_length=100),
                          kind: PropertyKind | None = None,
                          purpose: Purpose | None = None,
                          q: str | None = Query(None, max_length=120),
                          min_price: float | None = Query(None, ge=0),
                          max_price: float | None = Query(None, ge=0),
                          minimum_bedrooms: int | None = Query(None, ge=0),
                          minimum_bathrooms: int | None = Query(None, ge=0),
                          min_area: float | None = Query(None, ge=0),
                          max_area: float | None = Query(None, ge=0),
                          furnished: bool | None = None,
                          ready_to_move: bool | None = None,
                          north: float | None = Query(None, ge=-90, le=90),
                          south: float | None = Query(None, ge=-90, le=90),
                          east: float | None = Query(None, ge=-180, le=180),
                          west: float | None = Query(None, ge=-180, le=180),
                          amenity: str | None = Query(None, max_length=80),
                          sort: Literal['newest', 'price_asc', 'price_desc', 'area_desc'] = 'newest',
                          mine: bool = False):
    conditions = [Property.status == ListingStatus.published]
    if mine:
        if not user or user.role not in (Role.owner, Role.admin, Role.broker):
            raise HTTPException(403, 'Agency account required')
        conditions = [Property.tenant_id == user.tenant_id]
        if user.role == Role.broker:
            conditions.append(Property.created_by == user.id)
    if agency_slug:
        agency_id = await db.scalar(select(Tenant.id).where(Tenant.slug == agency_slug, Tenant.active.is_(True)))
        if agency_id is None:
            return PropertyPage(items=[], total=0, page=pagination.page, size=pagination.size)
        conditions.append(Property.tenant_id == agency_id)
    if city:
        conditions.append(Property.city.ilike(f'%{city.strip()}%'))
    if society:
        conditions.append(Property.society.ilike(f'%{society.strip()}%'))
    if block:
        conditions.append(Property.block.ilike(f'%{block.strip()}%'))
    if kind:
        conditions.append(Property.kind == kind)
    if purpose:
        conditions.append(Property.purpose == purpose)
    if q:
        terms = f'%{q.strip()}%'
        conditions.append(or_(Property.title.ilike(terms), Property.description.ilike(terms),
                              Property.area_name.ilike(terms)))
    if min_price is not None:
        conditions.append(Property.price >= min_price)
    if max_price is not None:
        conditions.append(Property.price <= max_price)
    if minimum_bedrooms is not None:
        conditions.append(Property.bedrooms >= minimum_bedrooms)
    if minimum_bathrooms is not None:
        conditions.append(Property.bathrooms >= minimum_bathrooms)
    if min_area is not None:
        conditions.append(Property.area_sqft >= min_area)
    if max_area is not None:
        conditions.append(Property.area_sqft <= max_area)
    if furnished is not None:
        conditions.append(Property.furnished.is_(furnished))
    if ready_to_move is not None:
        conditions.append(Property.ready_to_move.is_(ready_to_move))
    if any(value is not None for value in (north, south, east, west)):
        if any(value is None for value in (north, south, east, west)) or north < south or east < west:
            raise HTTPException(422, 'Use complete bounding box: north >= south, east >= west')
        conditions.extend([Property.latitude.between(south, north), Property.longitude.between(west, east)])
    if amenity:
        conditions.append(Property.amenities.contains([amenity.strip()]))
    order = {
        'newest': [Property.created_at.desc(), Property.id.desc()],
        'price_asc': [Property.price.asc(), Property.id.asc()],
        'price_desc': [Property.price.desc(), Property.id.desc()],
        'area_desc': [Property.area_sqft.desc(), Property.id.desc()],
    }[sort]
    total = await db.scalar(select(func.count()).select_from(Property).where(*conditions))
    rows = (await db.scalars(select(Property).where(*conditions).order_by(*order)
                             .offset(pagination.offset).limit(pagination.size))).all()
    return PropertyPage(items=[PropertyResponse.model_validate(row) for row in rows],
                        total=total or 0, page=pagination.page, size=pagination.size)




@router.get('/saved', response_model=list[PropertyResponse])
async def saved_properties(db: DB, user: CurrentUser):
    """Published listings bookmarked by the authenticated user, across agencies."""
    rows = (await db.scalars(
        select(Property).join(Interaction, Interaction.property_id == Property.id)
        .where(Interaction.user_id == user.id, Interaction.action == InteractionKind.save,
               Property.status == ListingStatus.published)
        .distinct().order_by(Property.created_at.desc()).limit(50)
    )).all()
    return rows


@router.delete('/saved/{property_id}', status_code=204)
async def remove_saved_property(property_id: UUID, db: DB, user: CurrentUser):
    await db.execute(delete(Interaction).where(
        Interaction.user_id == user.id, Interaction.property_id == property_id,
        Interaction.action == InteractionKind.save,
    ))

@router.get('/{property_id}', response_model=PropertyResponse)
async def property_detail(property_id: UUID, db: DB, user: OptionalUser):
    item = await get_property(db, property_id)
    ensure_viewable(user, item)
    return item


@router.post('', response_model=PropertyResponse, status_code=201)
async def create_property(payload: PropertyCreate, db: DB,
                          user: Annotated[User, Depends(require_roles(Role.owner, Role.admin, Role.broker))]):
    if payload.status != ListingStatus.draft:
        raise HTTPException(422, 'Create a draft, upload photos, then publish the listing')
    data = payload.model_dump(exclude={'pg', 'portion'}, mode='python')
    data['photo_url'] = str(payload.photo_url) if payload.photo_url else None
    item = Property(**data, tenant_id=user.tenant_id, created_by=user.id,
                    photos=[], embedding=await encode(property_text(payload)))
    db.add(item)
    await db.flush()
    await assign_details(db, item, payload)
    await db.flush()
    # Newly inserted async ORM objects do not have selectin relationships loaded.
    # Pydantic must never initiate implicit IO (MissingGreenlet -> HTTP 500).
    await load_listing_relations(db, item)
    return PropertyResponse.model_validate(item)


@router.patch('/{property_id}', response_model=PropertyResponse)
async def update_property(property_id: UUID, payload: PropertyUpdate, db: DB,
                          user: Annotated[User, Depends(require_roles(Role.owner, Role.admin, Role.broker))]):
    item = await get_property(db, property_id, lock=True)
    enforce_editor(user, item)
    if item.version != payload.expected_version:
        raise HTTPException(409, 'Listing changed; reload before saving')
    changes = payload.model_dump(exclude_unset=True, exclude={'expected_version'})
    combined = property_input_from_existing(item)
    combined.update(changes)
    if changes.get('status') == ListingStatus.published and item.status != ListingStatus.published:
        raise HTTPException(422, 'Use the publish endpoint after completing the listing')
    if changes.get('kind') and changes['kind'] != item.kind:
        if combined['kind'] != PropertyKind.pg and 'pg' not in changes:
            combined['pg'] = None
        if combined['kind'] != PropertyKind.portion and 'portion' not in changes:
            combined['portion'] = None
    validated = PropertyCreate.model_validate(combined)
    data = validated.model_dump(exclude={'pg', 'portion'})
    data['photo_url'] = str(validated.photo_url) if validated.photo_url else None
    for key, value in data.items():
        setattr(item, key, value)
    item.embedding = await encode(property_text(validated))
    item.version += 1
    await assign_details(db, item, validated)
    if item.status == ListingStatus.published:
        readiness = listing_readiness(item)
        if not readiness['ready']:
            raise HTTPException(422, {'message': 'A published listing must remain complete', **readiness})
    await db.flush()
    await load_listing_relations(db, item)
    return PropertyResponse.model_validate(item)


@router.delete('/{property_id}', status_code=204)
async def archive_property(property_id: UUID, db: DB,
                           user: Annotated[User, Depends(require_roles(Role.owner, Role.admin, Role.broker))]):
    item = await get_property(db, property_id, lock=True)
    enforce_editor(user, item)
    item.status = ListingStatus.archived
    item.version += 1
    await db.flush()


def listing_readiness(item: Property) -> dict:
    """A publish gate plus editorial guidance; not a paid placement algorithm."""
    blockers: list[str] = []
    suggestions: list[str] = []
    if not any(photo.category == 'gallery' for photo in item.photos):
        blockers.append('Upload at least one genuine property photograph')
    if len(item.description.strip()) < 50:
        blockers.append('Write a detailed description of at least 50 characters')
    if not item.area_name.strip():
        blockers.append('Set the neighbourhood or locality')
    if sum(photo.category == 'gallery' for photo in item.photos) < 5:
        suggestions.append('Add five or more well-lit photographs for a stronger ad')
    if len(item.highlights or []) < 2:
        suggestions.append('Add at least two property selling points')
    if len(item.amenities or []) < 3:
        suggestions.append('Specify relevant amenities to improve discovery')
    if not item.contact_phone:
        suggestions.append('Add a direct agent or owner contact number')
    score = max(0, 100 - 25 * len(blockers) - 6 * len(suggestions))
    return {'ready': not blockers, 'blockers': blockers, 'suggestions': suggestions, 'score': score}


@router.get('/{property_id}/readiness')
async def check_readiness(property_id: UUID, db: DB,
                          user: Annotated[User, Depends(require_roles(Role.owner, Role.admin, Role.broker))]):
    item = await get_property(db, property_id)
    enforce_editor(user, item)
    return listing_readiness(item)


@router.get('/{property_id}/insights')
async def property_insights(property_id: UUID, db: DB,
                            user: Annotated[User, Depends(require_roles(Role.owner, Role.admin, Role.broker))]):
    """Private listing studio insight. Only public comparable ads enter the pricing sample."""
    item = await get_property(db, property_id)
    enforce_editor(user, item)
    conditions = (
        Property.status == ListingStatus.published,
        Property.id != item.id,
        Property.city.ilike(item.city.strip()),
        Property.area_name.ilike(item.area_name.strip()),
        Property.kind == item.kind,
        Property.purpose == item.purpose,
        Property.currency == item.currency,
        Property.area_sqft.between(item.area_sqft * Decimal('0.7'), item.area_sqft * Decimal('1.3')),
    )
    comparable_prices = (await db.scalars(
        select(Property.price).where(*conditions)
        .order_by(Property.created_at.desc(), Property.id.desc()).limit(100)
    )).all()
    duplicate_count = await db.scalar(
        select(func.count(Property.id)).where(
            Property.id != item.id, Property.tenant_id == item.tenant_id,
            Property.title.ilike(item.title.strip()),
            Property.status != ListingStatus.archived,
        )
    ) or 0
    return calculate_market_insights(
        asking_price=item.price, area_sqft=item.area_sqft,
        comparable_prices=list(comparable_prices), duplicate_count=duplicate_count,
    )


@router.post('/{property_id}/publish', response_model=PropertyResponse)
async def publish_property(property_id: UUID, db: DB,
                           user: Annotated[User, Depends(require_roles(Role.owner, Role.admin, Role.broker))]):
    item = await get_property(db, property_id, lock=True)
    enforce_editor(user, item)
    readiness = listing_readiness(item)
    if not readiness['ready']:
        raise HTTPException(422, {'message': 'Listing needs attention before publication', **readiness})
    item.status = ListingStatus.published
    item.version += 1
    await db.flush()
    await load_listing_relations(db, item)
    return PropertyResponse.model_validate(item)


@router.post('/{property_id}/unpublish', response_model=PropertyResponse)
async def unpublish_property(property_id: UUID, db: DB,
                             user: Annotated[User, Depends(require_roles(Role.owner, Role.admin, Role.broker))]):
    item = await get_property(db, property_id, lock=True)
    enforce_editor(user, item)
    item.status = ListingStatus.draft
    item.version += 1
    await db.flush()
    await load_listing_relations(db, item)
    return PropertyResponse.model_validate(item)
