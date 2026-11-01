import enum
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4
from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func, Float
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


def uid() -> UUID:
    return uuid4()


def enum_type(enum_cls: type[enum.Enum], name: str):
    return Enum(enum_cls, name=name, values_callable=lambda cls: [item.value for item in cls])


class Role(str, enum.Enum):
    owner = 'owner'
    admin = 'admin'
    broker = 'broker'
    customer = 'customer'


class PropertyKind(str, enum.Enum):
    house = 'house'
    commercial_building = 'commercial_building'
    plot = 'plot'
    apartment = 'apartment'
    portion = 'portion'
    pg = 'pg'


class Purpose(str, enum.Enum):
    sale = 'sale'
    rent = 'rent'


class ListingStatus(str, enum.Enum):
    draft = 'draft'
    published = 'published'
    archived = 'archived'


class PortionKind(str, enum.Enum):
    upper = 'upper'
    lower = 'lower'
    floor = 'floor'


class RoomType(str, enum.Enum):
    single = 'single'
    twin = 'twin'
    dormitory = 'dormitory'


class LeadStatus(str, enum.Enum):
    new = 'new'
    contacted = 'contacted'
    qualified = 'qualified'
    won = 'won'
    lost = 'lost'


class InteractionKind(str, enum.Enum):
    view = 'view'
    save = 'save'
    inquiry = 'inquiry'


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Tenant(Base, Timestamped):
    __tablename__ = 'tenants'
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(160))
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default='true')
    public_description: Mapped[str] = mapped_column(Text, default='', server_default='')
    public_city: Mapped[str] = mapped_column(String(100), default='', server_default='')
    public_phone: Mapped[str | None] = mapped_column(String(40))
    public_email: Mapped[str | None] = mapped_column(String(255))


class User(Base, Timestamped):
    __tablename__ = 'users'
    __table_args__ = (UniqueConstraint('tenant_id', 'email', name='uq_users_tenant_email'),)
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uid)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey('tenants.id'), index=True)
    email: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(160))
    password_digest: Mapped[str] = mapped_column(Text)
    role: Mapped[Role] = mapped_column(enum_type(Role, 'user_role'))
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default='true')
    preferences: Mapped[dict] = mapped_column(JSONB, default=dict, server_default='{}')


class RefreshToken(Base):
    __tablename__ = 'refresh_tokens'
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uid)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey('tenants.id'), index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey('users.id'), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Property(Base, Timestamped):
    __tablename__ = 'properties'
    __table_args__ = (
        CheckConstraint('area_sqft > 0', name='ck_property_positive_area'),
        CheckConstraint('price > 0', name='ck_property_positive_price'),
        CheckConstraint("kind <> 'pg' OR purpose = 'rent'", name='ck_pg_rent_only'),
        Index('ix_properties_public_search', 'status', 'city', 'kind', 'purpose'),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uid)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey('tenants.id'), index=True)
    created_by: Mapped[UUID] = mapped_column(ForeignKey('users.id'))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default='')
    kind: Mapped[PropertyKind] = mapped_column(enum_type(PropertyKind, 'property_kind'))
    purpose: Mapped[Purpose] = mapped_column(enum_type(Purpose, 'listing_purpose'))
    status: Mapped[ListingStatus] = mapped_column(enum_type(ListingStatus, 'listing_status'), default=ListingStatus.draft)
    city: Mapped[str] = mapped_column(String(100), index=True)
    area_name: Mapped[str] = mapped_column(String(120), default='')
    address: Mapped[str] = mapped_column(String(255), default='')
    society: Mapped[str] = mapped_column(String(120), default='', server_default='')
    block: Mapped[str] = mapped_column(String(100), default='', server_default='')
    price_negotiable: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')
    ready_to_move: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')
    video_url: Mapped[str | None] = mapped_column(String(350))
    price: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    currency: Mapped[str] = mapped_column(String(3), default='PKR')
    area_sqft: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    bedrooms: Mapped[int] = mapped_column(Integer, default=0)
    bathrooms: Mapped[int] = mapped_column(Integer, default=0)
    furnished: Mapped[bool] = mapped_column(Boolean, default=False)
    amenities: Mapped[list] = mapped_column(JSONB, default=list, server_default='[]')
    highlights: Mapped[list] = mapped_column(JSONB, default=list, server_default='[]')
    contact_phone: Mapped[str | None] = mapped_column(String(40))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    photo_url: Mapped[str | None] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384))
    version: Mapped[int] = mapped_column(Integer, default=1)
    photos: Mapped[list['PropertyPhoto']] = relationship(
        back_populates='listing', cascade='all, delete-orphan', lazy='selectin',
        order_by=lambda: (PropertyPhoto.position, PropertyPhoto.created_at),
    )
    pg: Mapped['PGDetails | None'] = relationship(back_populates='property', uselist=False, cascade='all, delete-orphan', lazy='selectin')
    portion: Mapped['PortionDetails | None'] = relationship(back_populates='property', uselist=False, cascade='all, delete-orphan', lazy='selectin', foreign_keys='PortionDetails.property_id')


class PropertyPhoto(Base):
    """Metadata only. Bytes are stored outside the publicly exposed web root."""
    __tablename__ = 'property_photos'
    __table_args__ = (
        Index('ix_property_photos_order', 'property_id', 'position'),
        CheckConstraint('position >= 0', name='ck_photo_position'),
        CheckConstraint('byte_size > 0 AND width > 0 AND height > 0', name='ck_photo_dimensions'),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uid)
    property_id: Mapped[UUID] = mapped_column(ForeignKey('properties.id', ondelete='CASCADE'), index=True)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey('tenants.id'), index=True)
    object_key: Mapped[str] = mapped_column(String(255), unique=True)
    thumbnail_key: Mapped[str] = mapped_column(String(255), unique=True)
    alt_text: Mapped[str] = mapped_column(String(180), default='')
    category: Mapped[str] = mapped_column(String(20), default='gallery', server_default='gallery')
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    byte_size: Mapped[int] = mapped_column(Integer)
    position: Mapped[int] = mapped_column(Integer, default=0)
    is_cover: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    listing: Mapped[Property] = relationship(back_populates='photos')

    @property
    def url(self) -> str:
        return f'/api/v1/listings/{self.property_id}/photos/{self.id}/file'

    @property
    def thumbnail_url(self) -> str:
        return f'{self.url}?variant=thumb'


class PGDetails(Base):
    __tablename__ = 'pg_details'
    property_id: Mapped[UUID] = mapped_column(ForeignKey('properties.id', ondelete='CASCADE'), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey('tenants.id'), index=True)
    room_type: Mapped[RoomType] = mapped_column(enum_type(RoomType, 'room_type'))
    total_beds: Mapped[int] = mapped_column(Integer)
    available_beds: Mapped[int] = mapped_column(Integer)
    food_included: Mapped[bool] = mapped_column(Boolean, default=False)
    rules: Mapped[dict] = mapped_column(JSONB, default=dict)
    __table_args__ = (CheckConstraint('total_beds > 0 AND available_beds >= 0 AND available_beds <= total_beds', name='ck_pg_beds'),)
    property: Mapped[Property] = relationship(back_populates='pg')


class PortionDetails(Base):
    __tablename__ = 'portion_details'
    property_id: Mapped[UUID] = mapped_column(ForeignKey('properties.id', ondelete='CASCADE'), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey('tenants.id'), index=True)
    portion_kind: Mapped[PortionKind] = mapped_column(enum_type(PortionKind, 'portion_kind'))
    floor_number: Mapped[int | None] = mapped_column(Integer)
    separate_electricity_meter: Mapped[bool] = mapped_column(Boolean, default=False)
    separate_gas_meter: Mapped[bool] = mapped_column(Boolean, default=False)
    separate_water_meter: Mapped[bool] = mapped_column(Boolean, default=False)
    parent_property_id: Mapped[UUID | None] = mapped_column(ForeignKey('properties.id'))
    property: Mapped[Property] = relationship(back_populates='portion', foreign_keys=[property_id])


class Lead(Base, Timestamped):
    __tablename__ = 'leads'
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uid)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey('tenants.id'), index=True)
    property_id: Mapped[UUID] = mapped_column(ForeignKey('properties.id'))
    customer_user_id: Mapped[UUID | None] = mapped_column(ForeignKey('users.id'))
    contact_name: Mapped[str] = mapped_column(String(160))
    contact_email: Mapped[str] = mapped_column(String(255))
    contact_phone: Mapped[str | None] = mapped_column(String(40))
    message: Mapped[str] = mapped_column(Text, default='')
    status: Mapped[LeadStatus] = mapped_column(enum_type(LeadStatus, 'lead_status'), default=LeadStatus.new)
    notes: Mapped[str] = mapped_column(Text, default='')
    budget: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))


class MarketTrend(Base):
    __tablename__ = 'market_trends'
    __table_args__ = (UniqueConstraint('city', 'area_name', 'month', 'kind', name='uq_trend_area_month_kind'),)
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uid)
    city: Mapped[str] = mapped_column(String(100), index=True)
    area_name: Mapped[str] = mapped_column(String(120), default='')
    month: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    kind: Mapped[PropertyKind] = mapped_column(enum_type(PropertyKind, 'property_kind',))
    median_sale_price: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    median_monthly_rent: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    sample_size: Mapped[int] = mapped_column(Integer, default=0)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(160), default='')


class AIPrediction(Base):
    __tablename__ = 'ai_predictions'
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uid)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey('tenants.id'), index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey('users.id'))
    property_id: Mapped[UUID | None] = mapped_column(ForeignKey('properties.id'))
    purpose: Mapped[Purpose] = mapped_column(enum_type(Purpose, 'listing_purpose'))
    estimated_price: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    algorithm: Mapped[str] = mapped_column(String(100))
    training_count: Mapped[int] = mapped_column(Integer)
    model_mae: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Interaction(Base):
    __tablename__ = 'interactions'
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uid)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey('tenants.id'), index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey('users.id'), index=True)
    property_id: Mapped[UUID] = mapped_column(ForeignKey('properties.id'), index=True)
    action: Mapped[InteractionKind] = mapped_column(enum_type(InteractionKind, 'interaction_kind'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SavedSearch(Base, Timestamped):
    """User-owned search preferences. Alerts are in-app match counts, not outbound email."""
    __tablename__ = 'saved_searches'
    __table_args__ = (Index('ix_saved_searches_owner', 'tenant_id', 'user_id'),)
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uid)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey('tenants.id'), nullable=False)
    user_id: Mapped[UUID] = mapped_column(ForeignKey('users.id'), nullable=False)
    name: Mapped[str] = mapped_column(String(120))
    filters: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    alerts_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default='true')
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ViewingRequest(Base, Timestamped):
    """A viewing request belongs to the listing agency, but is readable by its customer."""
    __tablename__ = 'viewing_requests'
    __table_args__ = (
        Index('ix_viewings_agency_time', 'tenant_id', 'preferred_at'),
        Index('ix_viewings_customer', 'customer_user_id', 'created_at'),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uid)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey('tenants.id'), nullable=False)
    property_id: Mapped[UUID] = mapped_column(ForeignKey('properties.id'), nullable=False)
    customer_user_id: Mapped[UUID] = mapped_column(ForeignKey('users.id'), nullable=False)
    preferred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    contact_name: Mapped[str] = mapped_column(String(160))
    contact_phone: Mapped[str] = mapped_column(String(40))
    note: Mapped[str] = mapped_column(String(1000), default='', server_default='')
    status: Mapped[str] = mapped_column(String(20), default='requested', server_default='requested')
