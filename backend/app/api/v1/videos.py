"""Private, bounded property-video uploads.

No videos are served from the static frontend. Listing visibility is checked on
all reads, and writes use the existing tenant/creator authorization rules.
"""
import os
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from app.api.deps import DB, OptionalUser, require_roles
from app.api.v1.listings import enforce_editor, ensure_viewable, get_property
from app.models.entities import PropertyVideo, Role, User, ListingStatus
from app.services.media import media_path

router = APIRouter(prefix='/listings/{property_id}/video', tags=['Listing videos'])
MAX_BYTES = 80 * 1024 * 1024


def sniff(data: bytes) -> tuple[str, str]:
    if len(data) >= 12 and data[4:8] == b'ftyp':
        return 'video/mp4', '.mp4'
    if data.startswith(b'\x1a\x45\xdf\xa3'):
        return 'video/webm', '.webm'
    raise HTTPException(422, 'Only MP4 and WebM videos are supported')


@router.put('', status_code=201)
async def upload_video(property_id: UUID, db: DB,
                       user: Annotated[User, Depends(require_roles(Role.owner, Role.admin, Role.broker))],
                       file: Annotated[UploadFile, File()]):
    listing = await get_property(db, property_id, lock=True)
    enforce_editor(user, listing)
    first = await file.read(32)
    mime, suffix = sniff(first)
    key = f'{user.tenant_id}/{property_id}/video-{uuid4().hex}{suffix}'
    destination = media_path(key)
    destination.parent.mkdir(parents=True, exist_ok=True)
    staged = destination.with_name(destination.name + '.upload')
    total = len(first)
    try:
        with staged.open('xb') as handle:
            handle.write(first)
            while block := await file.read(1024 * 1024):
                total += len(block)
                if total > MAX_BYTES:
                    raise HTTPException(413, 'Video exceeds 80 MB')
                handle.write(block)
        if total <= 32:
            raise HTTPException(422, 'Video is incomplete')
        os.replace(staged, destination)
        existing = await db.scalar(select(PropertyVideo).where(PropertyVideo.property_id == property_id).with_for_update())
        if existing is None:
            db.add(PropertyVideo(property_id=property_id, tenant_id=user.tenant_id,
                                 object_key=key, mime_type=mime, byte_size=total))
        else:
            # Previous file is swept separately; do not delete inside an open DB transaction.
            existing.object_key, existing.mime_type, existing.byte_size = key, mime, total
        await db.flush()
    except Exception:
        staged.unlink(missing_ok=True)
        destination.unlink(missing_ok=True)
        raise
    finally:
        await file.close()
    return {'message': 'Video uploaded', 'byte_size': total}


@router.get('')
async def video_info(property_id: UUID, db: DB, user: OptionalUser):
    listing = await get_property(db, property_id)
    ensure_viewable(user, listing)
    video = await db.scalar(select(PropertyVideo).where(PropertyVideo.property_id == property_id))
    return {'available': video is not None, 'byte_size': video.byte_size if video else None,
            'url': f'/api/v1/listings/{property_id}/video/file' if video else None}


@router.get('/file')
async def play_video(property_id: UUID, db: DB, user: OptionalUser):
    listing = await get_property(db, property_id)
    ensure_viewable(user, listing)
    video = await db.scalar(select(PropertyVideo).where(PropertyVideo.property_id == property_id))
    if not video:
        raise HTTPException(404, 'Video not found')
    path = media_path(video.object_key)
    if not path.is_file():
        raise HTTPException(404, 'Video file unavailable')
    cache = 'public, max-age=300' if listing.status == ListingStatus.published else 'private, no-store'
    return FileResponse(path, media_type=video.mime_type,
                        headers={'Cache-Control': cache, 'X-Content-Type-Options': 'nosniff'})


@router.delete('', status_code=204)
async def remove_video(property_id: UUID, db: DB,
                       user: Annotated[User, Depends(require_roles(Role.owner, Role.admin, Role.broker))]):
    listing = await get_property(db, property_id, lock=True)
    enforce_editor(user, listing)
    video = await db.scalar(select(PropertyVideo).where(PropertyVideo.property_id == property_id))
    if video:
        await db.delete(video)
        # Files are removed by the media sweep after commit.
