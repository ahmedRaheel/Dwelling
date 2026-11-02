from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.api.deps import DB, CurrentUser, require_roles
from app.core.database import set_scope
from app.core.security import create_token, decode_token, hash_password, token_digest, verify_password
from app.models.entities import RefreshToken, Role, Tenant, User
from app.schemas.domain import (CreateStaff, CustomerRegistration, LoginInput, PreferencesUpdate,
                                RefreshInput, TenantRegistration, TokenPair, UserResponse)

router = APIRouter(prefix='/auth', tags=['Authentication'])


async def issue_tokens(db, user: User, workspace_slug: str | None = None) -> TokenPair:
    access, _ = create_token(str(user.id), str(user.tenant_id), 'access')
    refresh, expires = create_token(str(user.id), str(user.tenant_id), 'refresh')
    db.add(RefreshToken(tenant_id=user.tenant_id, user_id=user.id, token_hash=token_digest(refresh), expires_at=expires))
    await db.flush()
    if workspace_slug is None:
        workspace_slug = await db.scalar(select(Tenant.slug).where(Tenant.id == user.tenant_id))
    return TokenPair(access_token=access, refresh_token=refresh, workspace_slug=workspace_slug)


async def get_tenant(db, slug: str) -> Tenant:
    tenant = await db.scalar(select(Tenant).where(Tenant.slug == slug, Tenant.active.is_(True)))
    if tenant is None:
        raise HTTPException(404, 'Agency not found')
    return tenant


@router.post('/tenant/register', response_model=TokenPair, status_code=201)
async def create_tenant(payload: TenantRegistration, db: DB):
    if await db.scalar(select(Tenant).where(Tenant.slug == payload.slug)):
        raise HTTPException(409, 'Agency slug already taken')
    tenant = Tenant(id=uuid4(), name=payload.agency_name, slug=payload.slug, account_type=payload.account_type)
    await set_scope(db, tenant.id)
    user = User(tenant_id=tenant.id, full_name=payload.full_name, email=str(payload.email).lower(),
                password_digest=hash_password(payload.password), role=Role.owner)
    db.add_all([tenant, user])
    try:
        await db.flush()
    except IntegrityError as exc:
        raise HTTPException(409, 'Agency slug or account already exists') from exc
    await set_scope(db, tenant.id, user.id)
    return await issue_tokens(db, user)


@router.post('/register', response_model=TokenPair, status_code=201)
async def register_customer(payload: CustomerRegistration, db: DB):
    if payload.tenant_slug:
        tenant = await get_tenant(db, payload.tenant_slug)
    else:
        # Independent buyers need no agency invitation or existing workspace.
        # The random workspace slug is returned with the tokens for later login.
        tenant = Tenant(id=uuid4(), name=f'{payload.full_name} · Personal',
                        slug=f'home-{uuid4().hex[:16]}', account_type='customer')
        db.add(tenant)
    await set_scope(db, tenant.id)
    user = User(tenant_id=tenant.id, full_name=payload.full_name, email=str(payload.email).lower(),
                password_digest=hash_password(payload.password), role=Role.customer)
    db.add(user)
    try:
        await db.flush()
    except IntegrityError as exc:
        raise HTTPException(409, 'Email already registered for this agency') from exc
    await set_scope(db, tenant.id, user.id)
    return await issue_tokens(db, user)


@router.post('/login', response_model=TokenPair)
async def login(payload: LoginInput, db: DB):
    tenant = await get_tenant(db, payload.tenant_slug)
    await set_scope(db, tenant.id)
    user = await db.scalar(select(User).where(User.tenant_id == tenant.id, User.email == str(payload.email).lower()))
    if user is None or not user.active or not verify_password(payload.password, user.password_digest):
        raise HTTPException(401, 'Invalid credentials')
    await set_scope(db, tenant.id, user.id)
    return await issue_tokens(db, user)


@router.post('/refresh', response_model=TokenPair)
async def refresh(payload: RefreshInput, db: DB):
    claims = decode_token(payload.refresh_token, 'refresh')
    try:
        tenant_id, user_id = UUID(claims['tid']), UUID(claims['sub'])
    except (ValueError, KeyError) as exc:
        raise HTTPException(401, 'Invalid credentials') from exc
    await set_scope(db, tenant_id, user_id)
    record = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_digest(payload.refresh_token)).with_for_update())
    now = datetime.now(timezone.utc)
    if record is None or record.revoked_at or record.expires_at <= now or record.user_id != user_id:
        raise HTTPException(401, 'Refresh token revoked or expired')
    user = await db.scalar(select(User).where(User.id == user_id, User.tenant_id == tenant_id, User.active.is_(True)))
    if not user:
        raise HTTPException(401, 'Account unavailable')
    record.revoked_at = now
    return await issue_tokens(db, user)


@router.post('/logout', status_code=204)
async def logout(payload: RefreshInput, db: DB):
    # Logout remains possible if the access token has already expired.
    try:
        claims = decode_token(payload.refresh_token, 'refresh')
        tenant_id, user_id = UUID(claims['tid']), UUID(claims['sub'])
    except (HTTPException, ValueError, KeyError):
        return None
    await set_scope(db, tenant_id, user_id)
    record = await db.scalar(select(RefreshToken).where(
        RefreshToken.token_hash == token_digest(payload.refresh_token),
        RefreshToken.user_id == user_id).with_for_update())
    if record and record.revoked_at is None:
        record.revoked_at = datetime.now(timezone.utc)
    return None


@router.get('/me', response_model=UserResponse)
async def me(user: CurrentUser, db: DB):
    tenant = await db.scalar(select(Tenant).where(Tenant.id == user.tenant_id))
    return UserResponse.model_validate(user).model_copy(update={
        'account_type': tenant.account_type if tenant else None,
        'workspace_slug': tenant.slug if tenant else None,
    })


@router.patch('/me/preferences', response_model=UserResponse)
async def update_preferences(payload: PreferencesUpdate, db: DB, user: CurrentUser):
    user.preferences = payload.model_dump(mode='json', exclude_none=True)
    await db.flush()
    return user


@router.post('/staff', response_model=UserResponse, status_code=201)
async def create_staff(payload: CreateStaff, db: DB,
                       user: Annotated[User, Depends(require_roles(Role.owner, Role.admin))]):
    if payload.role not in (Role.broker, Role.admin):
        raise HTTPException(422, 'Staff role must be broker or admin')
    staff = User(tenant_id=user.tenant_id, full_name=payload.full_name, email=str(payload.email).lower(),
                 password_digest=hash_password(payload.password), role=payload.role)
    db.add(staff)
    try:
        await db.flush()
    except IntegrityError as exc:
        raise HTTPException(409, 'Account already exists') from exc
    return staff
