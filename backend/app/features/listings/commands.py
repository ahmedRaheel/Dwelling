"""Listing write use-cases. Async persistence boundaries live here, not in response serialization."""
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.entities import Property, PropertyKind, PGDetails, PortionDetails
from app.schemas.domain import PropertyCreate

async def validate_parent(db: AsyncSession, tenant_id: UUID, kind: PropertyKind, parent_id: UUID | None, own_id: UUID | None = None):
    if parent_id is None:
        return
    if parent_id == own_id:
        raise HTTPException(422, 'A portion cannot contain itself')
    parent = await db.scalar(select(Property).where(Property.id == parent_id, Property.tenant_id == tenant_id))
    if not parent or parent.kind not in (PropertyKind.house, PropertyKind.commercial_building):
        raise HTTPException(422, 'Parent must be a house/building owned by your agency')


async def assign_details(db: AsyncSession, item: Property, payload: PropertyCreate):
    # An async SQLAlchemy relationship must never be read while unloaded:
    # `if item.pg` and `if item.portion` otherwise invoke synchronous lazy IO,
    # raising MissingGreenlet on freshly flushed Property instances.
    # Explicitly load both relationships *before* testing or modifying them.
    await db.refresh(item, attribute_names=['pg', 'portion'])
    if payload.kind == PropertyKind.pg and payload.pg:
        details = payload.pg.model_dump()
        if item.pg is None:
            item.pg = PGDetails(property_id=item.id, tenant_id=item.tenant_id, **details)
        else:
            for key, value in details.items():
                setattr(item.pg, key, value)
        if item.portion:
            await db.delete(item.portion)
            item.portion = None
    elif payload.kind == PropertyKind.portion and payload.portion:
        await validate_parent(db, item.tenant_id, payload.kind, payload.portion.parent_property_id, item.id)
        details = payload.portion.model_dump()
        if item.portion is None:
            item.portion = PortionDetails(property_id=item.id, tenant_id=item.tenant_id, **details)
        else:
            for key, value in details.items():
                setattr(item.portion, key, value)
        if item.pg:
            await db.delete(item.pg)
            item.pg = None
    else:
        if item.pg:
            await db.delete(item.pg)
            item.pg = None
        if item.portion:
            await db.delete(item.portion)
            item.portion = None


async def load_listing_relations(db: AsyncSession, item: Property) -> Property:
    """Explicit async IO for relationships needed by read models and publication guards."""
    await db.refresh(item, attribute_names=['photos', 'pg', 'portion'])
    return item
