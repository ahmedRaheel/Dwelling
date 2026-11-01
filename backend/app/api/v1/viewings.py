"""Customer appointments and agency scheduling inbox; request is not confirmation."""
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from app.api.deps import DB, CurrentUser, require_roles
from app.models.entities import Property, Role, User, ViewingRequest
from app.schemas.domain import ViewingCreate, ViewingResponse, ViewingStatusUpdate

router = APIRouter(prefix='/viewings', tags=['Property viewing requests'])
Staff = Annotated[User, Depends(require_roles(Role.owner, Role.admin, Role.broker))]


@router.post('', status_code=201)
async def request_viewing(payload: ViewingCreate, db: DB, user: CurrentUser):
    viewing_id = await db.scalar(text('SELECT public.request_property_viewing(:property, :when, :name, :phone, :note)'), {
        'property': payload.property_id, 'when': payload.preferred_at,
        'name': payload.contact_name, 'phone': payload.contact_phone, 'note': payload.note,
    })
    return {'id': viewing_id, 'status': 'requested',
            'message': 'Request submitted. The agency must confirm your appointment.'}


@router.get('/mine', response_model=list[ViewingResponse])
async def my_viewings(db: DB, user: CurrentUser):
    return (await db.scalars(select(ViewingRequest).where(
        ViewingRequest.customer_user_id == user.id
    ).order_by(ViewingRequest.created_at.desc()).limit(100))).all()


@router.get('/agency', response_model=list[ViewingResponse])
async def agency_viewings(db: DB, user: Staff):
    query = select(ViewingRequest).join(Property, Property.id == ViewingRequest.property_id).where(
        ViewingRequest.tenant_id == user.tenant_id)
    if user.role == Role.broker:
        query = query.where(Property.created_by == user.id)
    return (await db.scalars(query.order_by(ViewingRequest.preferred_at.asc()).limit(200))).all()


@router.patch('/{viewing_id}', response_model=ViewingResponse)
async def change_viewing_status(viewing_id: UUID, payload: ViewingStatusUpdate, db: DB, user: CurrentUser):
    query = select(ViewingRequest).where(ViewingRequest.id == viewing_id).with_for_update()
    item = await db.scalar(query)
    if not item:
        raise HTTPException(404, 'Viewing request not found')
    if item.customer_user_id == user.id and payload.status == 'cancelled':
        if item.status not in ('requested', 'confirmed'):
            raise HTTPException(409, 'This appointment can no longer be cancelled')
    elif user.role in (Role.owner, Role.admin, Role.broker) and item.tenant_id == user.tenant_id:
        property_obj = await db.get(Property, item.property_id)
        if user.role == Role.broker and property_obj.created_by != user.id:
            raise HTTPException(403, 'Only the assigned broker can manage this appointment')
        valid = {
            'requested': {'confirmed', 'declined', 'cancelled'},
            'confirmed': {'completed', 'declined', 'cancelled'},
        }
        if payload.status not in valid.get(item.status, set()):
            raise HTTPException(409, 'Invalid appointment status transition')
    else:
        raise HTTPException(403, 'Not authorized to change this appointment')
    item.status = payload.status
    await db.flush()
    return item
