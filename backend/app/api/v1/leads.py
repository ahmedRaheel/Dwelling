from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from app.api.deps import DB, CurrentUser, require_roles
from app.api.v1.listings import get_property
from app.models.entities import Lead, ListingStatus, Property, Role, User
from app.schemas.domain import CustomerInquiryResponse, InquiryInput, LeadCreate, LeadResponse, LeadUpdate

router = APIRouter(prefix='/leads', tags=['Broker CRM'])


@router.post('/inquiries', status_code=201)
async def submit_inquiry(payload: InquiryInput, db: DB, user: CurrentUser):
    listing = await get_property(db, payload.property_id)
    if listing.status != ListingStatus.published:
        raise HTTPException(422, 'Only published listings accept inquiries')
    # Minimal, tightly constrained SECURITY DEFINER function bridges customer and listing tenants.
    lead_id = await db.scalar(text('SELECT public.submit_property_inquiry(:property_id, :name, :email, :phone, :message, :budget)'),
                              {'property_id': payload.property_id, 'name': payload.contact_name,
                               'email': str(payload.contact_email), 'phone': payload.contact_phone,
                               'message': payload.message, 'budget': payload.budget})
    return {'id': lead_id, 'message': 'Inquiry submitted'}


@router.get('/mine', response_model=list[CustomerInquiryResponse])
async def my_inquiries(db: DB, user: CurrentUser):
    records = (await db.scalars(select(Lead).where(Lead.customer_user_id == user.id).order_by(Lead.created_at.desc()).limit(100))).all()
    return records


@router.get('', response_model=list[LeadResponse])
async def list_leads(db: DB, user: Annotated[User, Depends(require_roles(Role.owner, Role.admin, Role.broker))]):
    return (await db.scalars(select(Lead).where(Lead.tenant_id == user.tenant_id)
                             .order_by(Lead.created_at.desc()).limit(200))).all()


@router.post('', response_model=LeadResponse, status_code=201)
async def create_lead(payload: LeadCreate, db: DB,
                      user: Annotated[User, Depends(require_roles(Role.owner, Role.admin, Role.broker))]):
    item = await db.scalar(select(Property).where(Property.id == payload.property_id, Property.tenant_id == user.tenant_id))
    if not item:
        raise HTTPException(404, 'Listing does not belong to this agency')
    lead = Lead(tenant_id=user.tenant_id, customer_user_id=None,
                **payload.model_dump(exclude={'contact_email'}), contact_email=str(payload.contact_email))
    db.add(lead)
    await db.flush()
    return lead


@router.patch('/{lead_id}', response_model=LeadResponse)
async def update_lead(lead_id: UUID, payload: LeadUpdate, db: DB,
                      user: Annotated[User, Depends(require_roles(Role.owner, Role.admin, Role.broker))]):
    lead = await db.scalar(select(Lead).where(Lead.id == lead_id, Lead.tenant_id == user.tenant_id))
    if lead is None:
        raise HTTPException(404, 'Lead not found')
    lead.status = payload.status
    lead.notes = payload.notes
    await db.flush()
    return lead
