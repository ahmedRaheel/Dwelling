from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, model_validator, field_validator
from app.models.entities import (InteractionKind, LeadStatus, ListingStatus, PortionKind, PropertyKind,
                                 Purpose, Role, RoomType)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class TenantRegistration(StrictModel):
    account_type: str = Field(default='agency', pattern=r'^(agency|owner|broker|dealer)$')
    agency_name: str = Field(min_length=2, max_length=160)
    slug: str = Field(pattern=r'^[a-z0-9][a-z0-9-]{2,49}$')
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class CustomerRegistration(StrictModel):
    tenant_slug: str | None = Field(default=None, max_length=80)
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class LoginInput(StrictModel):
    tenant_slug: str
    email: EmailStr
    password: str


class RefreshInput(StrictModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = 'bearer'
    workspace_slug: str | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    email: EmailStr
    full_name: str
    role: Role
    preferences: dict
    account_type: str | None = None
    workspace_slug: str | None = None


class CreateStaff(StrictModel):
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    role: Role


class PreferencesUpdate(StrictModel):
    city: str | None = Field(default=None, max_length=100)
    kind: PropertyKind | None = None
    purpose: Purpose | None = None
    max_price: Decimal | None = Field(default=None, gt=0)
    minimum_bedrooms: int | None = Field(default=None, ge=0, le=30)


class PGInput(StrictModel):
    room_type: RoomType
    total_beds: int = Field(gt=0, le=1000)
    available_beds: int = Field(ge=0, le=1000)
    food_included: bool = False
    rules: dict[str, str | int | bool | list[str]] = Field(default_factory=dict)

    @model_validator(mode='after')
    def check_beds(self):
        if self.available_beds > self.total_beds:
            raise ValueError('Available beds must not exceed total beds')
        return self


class PortionInput(StrictModel):
    portion_kind: PortionKind
    floor_number: int | None = Field(default=None, ge=-2, le=150)
    separate_electricity_meter: bool = False
    separate_gas_meter: bool = False
    separate_water_meter: bool = False
    parent_property_id: UUID | None = None

    @model_validator(mode='after')
    def check_floor(self):
        if self.portion_kind == PortionKind.floor and self.floor_number is None:
            raise ValueError('Floor number is required for a floor-wise portion')
        return self


class PropertyCreate(StrictModel):
    title: str = Field(min_length=5, max_length=200)
    description: str = Field(default='', max_length=10000)
    kind: PropertyKind
    purpose: Purpose
    status: ListingStatus = ListingStatus.draft
    city: str = Field(min_length=2, max_length=100)
    area_name: str = Field(default='', max_length=120)
    address: str = Field(default='', max_length=255)
    society: str = Field(default='', max_length=120)
    block: str = Field(default='', max_length=100)
    price_negotiable: bool = False
    ready_to_move: bool = False
    video_url: str | None = Field(default=None, max_length=350)
    price: Decimal = Field(gt=0, max_digits=16, decimal_places=2)
    currency: str = Field(default='PKR', pattern=r'^[A-Z]{3}$')
    area_sqft: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    bedrooms: int = Field(default=0, ge=0, le=100)
    bathrooms: int = Field(default=0, ge=0, le=100)
    furnished: bool = False
    photo_url: HttpUrl | None = None
    amenities: list[str] = Field(default_factory=list, max_length=40)
    highlights: list[str] = Field(default_factory=list, max_length=8)
    contact_phone: str | None = Field(default=None, min_length=7, max_length=40, pattern=r'^[+0-9() .-]+$')
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    pg: PGInput | None = None
    portion: PortionInput | None = None

    @field_validator('video_url')
    @classmethod
    def validate_video(cls, value: str | None):
        if value is None or value == '':
            return None
        from urllib.parse import urlsplit
        url = urlsplit(value)
        if url.scheme != 'https' or url.hostname not in {'youtube.com', 'www.youtube.com', 'youtu.be', 'vimeo.com', 'www.vimeo.com'} or url.username or url.password:
            raise ValueError('Use an HTTPS YouTube or Vimeo video link')
        return value

    @model_validator(mode='after')
    def check_location(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError('Latitude and longitude must be supplied together')
        if any(not item.strip() or len(item) > 80 for item in self.amenities):
            raise ValueError('Amenities must be non-empty and at most 80 characters')
        if any(not item.strip() or len(item) > 140 for item in self.highlights):
            raise ValueError('Highlights must be non-empty and at most 140 characters')
        return self

    @model_validator(mode='after')
    def check_details(self):
        if self.kind == PropertyKind.pg:
            if self.purpose != Purpose.rent or self.pg is None or self.portion is not None:
                raise ValueError('PG requires rent purpose and PG details only')
        elif self.kind == PropertyKind.portion:
            if self.portion is None or self.pg is not None:
                raise ValueError('Portion details required for portion listings only')
        elif self.pg is not None or self.portion is not None:
            raise ValueError('PG/portion details can only be specified for their property kinds')
        return self


class PropertyUpdate(StrictModel):
    expected_version: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=5, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    kind: PropertyKind | None = None
    purpose: Purpose | None = None
    status: ListingStatus | None = None
    city: str | None = Field(default=None, min_length=2, max_length=100)
    area_name: str | None = Field(default=None, max_length=120)
    address: str | None = Field(default=None, max_length=255)
    society: str | None = Field(default=None, max_length=120)
    block: str | None = Field(default=None, max_length=100)
    price_negotiable: bool | None = None
    ready_to_move: bool | None = None
    video_url: str | None = Field(default=None, max_length=350)
    price: Decimal | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, pattern=r'^[A-Z]{3}$')
    area_sqft: Decimal | None = Field(default=None, gt=0)
    bedrooms: int | None = Field(default=None, ge=0, le=100)
    bathrooms: int | None = Field(default=None, ge=0, le=100)
    furnished: bool | None = None
    photo_url: HttpUrl | None = None
    amenities: list[str] | None = Field(default=None, max_length=40)
    highlights: list[str] | None = Field(default=None, max_length=8)
    contact_phone: str | None = Field(default=None, min_length=7, max_length=40, pattern=r'^[+0-9() .-]+$')
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    pg: PGInput | None = None
    portion: PortionInput | None = None


class PGResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    room_type: RoomType
    total_beds: int
    available_beds: int
    food_included: bool
    rules: dict


class PortionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    portion_kind: PortionKind
    floor_number: int | None
    separate_electricity_meter: bool
    separate_gas_meter: bool
    separate_water_meter: bool
    parent_property_id: UUID | None


class PropertyPhotoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    property_id: UUID
    alt_text: str
    category: str
    width: int
    height: int
    byte_size: int
    position: int
    is_cover: bool
    url: str
    thumbnail_url: str


class PhotoUpdate(StrictModel):
    alt_text: str | None = Field(default=None, max_length=180)
    is_cover: bool | None = None


class PhotoOrder(StrictModel):
    photo_ids: list[UUID] = Field(min_length=1, max_length=24)


class ListingReadiness(BaseModel):
    ready: bool
    blockers: list[str]
    suggestions: list[str]
    score: int


class PropertyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    title: str
    description: str
    kind: PropertyKind
    purpose: Purpose
    status: ListingStatus
    city: str
    area_name: str
    address: str
    society: str
    block: str
    price_negotiable: bool
    ready_to_move: bool
    video_url: str | None
    price: Decimal
    currency: str
    area_sqft: Decimal
    bedrooms: int
    bathrooms: int
    furnished: bool
    photo_url: str | None
    photos: list[PropertyPhotoResponse] = Field(default_factory=list)
    amenities: list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)
    contact_phone: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    pg: PGResponse | None
    portion: PortionResponse | None
    version: int
    created_at: datetime
    updated_at: datetime


class PropertyPage(BaseModel):
    items: list[PropertyResponse]
    total: int
    page: int
    size: int


class InquiryInput(StrictModel):
    property_id: UUID
    contact_name: str = Field(min_length=2, max_length=160)
    contact_email: EmailStr
    contact_phone: str | None = Field(default=None, max_length=40)
    message: str = Field(default='', max_length=4000)
    budget: Decimal | None = Field(default=None, gt=0)


class LeadCreate(InquiryInput):
    pass


class LeadUpdate(StrictModel):
    status: LeadStatus
    notes: str = Field(default='', max_length=4000)


class CustomerInquiryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    property_id: UUID
    message: str
    status: LeadStatus
    created_at: datetime


class LeadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    property_id: UUID
    customer_user_id: UUID | None
    contact_name: str
    contact_email: str
    contact_phone: str | None
    message: str
    status: LeadStatus
    notes: str
    budget: Decimal | None
    created_at: datetime


class InteractionInput(StrictModel):
    property_id: UUID
    action: InteractionKind


class PredictionFeatures(StrictModel):
    purpose: Purpose
    kind: PropertyKind
    city: str = Field(min_length=2, max_length=100)
    area_name: str = Field(default='', max_length=120)
    area_sqft: float = Field(gt=0, le=1e8)
    bedrooms: int = Field(ge=0, le=100)
    bathrooms: int = Field(ge=0, le=100)
    furnished: bool = False


class PredictionResult(BaseModel):
    status: str
    reason: str | None = None
    estimate: float | None = None
    currency: str = 'PKR'
    method: str | None = None
    sample_count: int = 0
    holdout_mae: float | None = None
    pricing_basis: str = 'published_asking_prices_not_closed_transactions'


class Recommendation(BaseModel):
    property: PropertyResponse
    score: float
    reasons: list[str]


class BrokerMatch(BaseModel):
    lead: LeadResponse
    property: PropertyResponse
    score: float
    reasons: list[str]


class TrendResponse(BaseModel):
    month: datetime
    city: str
    area_name: str
    kind: PropertyKind
    median_sale_price: Decimal | None
    median_monthly_rent: Decimal | None
    sample_size: int
    source: str


class RentForecast(BaseModel):
    status: str
    reason: str | None = None
    projected: list[dict[str, str | float]] = Field(default_factory=list)
    method: str | None = None
    currency: str = 'PKR'


class PropertySearchFilters(StrictModel):
    city: str | None = Field(default=None, max_length=100)
    society: str | None = Field(default=None, max_length=120)
    block: str | None = Field(default=None, max_length=100)
    q: str | None = Field(default=None, max_length=120)
    kind: PropertyKind | None = None
    purpose: Purpose | None = None
    min_price: Decimal | None = Field(default=None, ge=0)
    max_price: Decimal | None = Field(default=None, ge=0)
    minimum_bedrooms: int | None = Field(default=None, ge=0, le=100)
    minimum_bathrooms: int | None = Field(default=None, ge=0, le=100)
    min_area: Decimal | None = Field(default=None, ge=0)
    max_area: Decimal | None = Field(default=None, ge=0)
    furnished: bool | None = None
    ready_to_move: bool | None = None
    amenity: str | None = Field(default=None, max_length=80)

    @model_validator(mode='after')
    def verify_ranges(self):
        if self.min_price is not None and self.max_price is not None and self.min_price > self.max_price:
            raise ValueError('Minimum price must be below maximum price')
        if self.min_area is not None and self.max_area is not None and self.min_area > self.max_area:
            raise ValueError('Minimum area must be below maximum area')
        return self


class SavedSearchCreate(StrictModel):
    name: str = Field(min_length=2, max_length=120)
    filters: PropertySearchFilters
    alerts_enabled: bool = True


class SavedSearchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    filters: dict
    alerts_enabled: bool
    last_checked_at: datetime | None
    created_at: datetime


class SavedSearchMatches(BaseModel):
    search: SavedSearchResponse
    new_count: int
    items: list[PropertyResponse]


class AgencyUpdate(StrictModel):
    public_description: str = Field(default='', max_length=2000)
    public_city: str = Field(default='', max_length=100)
    public_phone: str | None = Field(default=None, max_length=40, pattern=r'^[+0-9() .-]+$')
    public_email: EmailStr | None = None


class AgencyResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    public_description: str
    public_city: str
    public_phone: str | None
    public_email: str | None
    published_listings: int


class ViewingCreate(StrictModel):
    property_id: UUID
    preferred_at: datetime
    contact_name: str = Field(min_length=2, max_length=160)
    contact_phone: str = Field(min_length=7, max_length=40, pattern=r'^[+0-9() .-]+$')
    note: str = Field(default='', max_length=1000)

    @model_validator(mode='after')
    def validate_date(self):
        from datetime import timedelta, timezone
        if self.preferred_at.tzinfo is None or not (datetime.now(timezone.utc) + timedelta(hours=1) <= self.preferred_at <= datetime.now(timezone.utc) + timedelta(days=90)):
            raise ValueError('Choose a timezone-aware viewing time between one hour and 90 days ahead')
        return self


class ViewingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    property_id: UUID
    preferred_at: datetime
    contact_name: str
    contact_phone: str
    note: str
    status: str
    created_at: datetime


class ViewingStatusUpdate(StrictModel):
    status: str = Field(pattern=r'^(confirmed|declined|completed|cancelled)$')
