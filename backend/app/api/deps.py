from typing import Annotated
from uuid import UUID
from fastapi import Depends, Header, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db, set_scope
from app.core.security import decode_token
from app.models.entities import Role, Tenant, User

DB = Annotated[AsyncSession, Depends(get_db, scope="function")]
bearer = HTTPBearer(auto_error=False)


async def optional_user(
    db: DB, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> User | None:
    if credentials is None:
        return None
    if credentials.scheme.lower() != 'bearer':
        raise HTTPException(401, 'Invalid authorization scheme')
    claims = decode_token(credentials.credentials, 'access')
    try:
        tenant_id = UUID(claims['tid'])
        user_id = UUID(claims['sub'])
    except (ValueError, KeyError) as exc:
        raise HTTPException(401, 'Invalid credentials') from exc
    await set_scope(db, tenant_id, user_id)
    user = await db.scalar(select(User).where(User.id == user_id, User.tenant_id == tenant_id, User.active.is_(True)))
    tenant = await db.scalar(select(Tenant).where(Tenant.id == tenant_id, Tenant.active.is_(True)))
    if not user or not tenant:
        raise HTTPException(401, 'Account or agency disabled or unavailable')
    return user


async def current_user(user: Annotated[User | None, Depends(optional_user)]) -> User:
    if user is None:
        raise HTTPException(401, 'Authentication required', headers={'WWW-Authenticate': 'Bearer'})
    return user


CurrentUser = Annotated[User, Depends(current_user)]
OptionalUser = Annotated[User | None, Depends(optional_user)]


def require_roles(*roles: Role):
    async def check(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(403, 'Insufficient permissions')
        return user
    return check


async def language(accept_language: Annotated[str | None, Header()] = None) -> str:
    return 'ur' if (accept_language or '').lower().startswith('ur') else 'en'


Lang = Annotated[str, Depends(language)]


class Pagination:
    def __init__(self, page: int = Query(1, ge=1), size: int = Query(12, ge=1, le=50)):
        self.page = page
        self.size = size
        self.offset = (page - 1) * size
