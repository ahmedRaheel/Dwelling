from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import uuid4
import jwt
from fastapi import HTTPException, status
from jwt import InvalidTokenError
from pwdlib import PasswordHash
from app.core.config import get_settings

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, digest: str) -> bool:
    return password_hash.verify(password, digest)


def create_token(user_id: str, tenant_id: str, kind: str) -> tuple[str, datetime]:
    cfg = get_settings()
    now = datetime.now(timezone.utc)
    lifetime = timedelta(minutes=cfg.access_token_minutes) if kind == 'access' else timedelta(days=cfg.refresh_token_days)
    expiry = now + lifetime
    payload = {'sub': user_id, 'tid': tenant_id, 'typ': kind, 'jti': str(uuid4()),
               'iss': cfg.jwt_issuer, 'iat': now, 'nbf': now, 'exp': expiry}
    return jwt.encode(payload, cfg.jwt_secret, algorithm='HS256'), expiry


def decode_token(token: str, kind: str) -> dict:
    cfg = get_settings()
    try:
        payload = jwt.decode(token, cfg.jwt_secret, algorithms=['HS256'], issuer=cfg.jwt_issuer,
                             options={'require': ['sub', 'tid', 'typ', 'jti', 'iss', 'exp', 'iat']})
        if payload.get('typ') != kind:
            raise InvalidTokenError('Invalid token type')
        return payload
    except InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid or expired credentials') from exc


def token_digest(raw: str) -> str:
    return sha256(raw.encode('utf-8')).hexdigest()
