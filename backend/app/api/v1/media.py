"""Authenticated gallery management, with public reads only for published ads."""
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select, update

from app.api.deps import DB, OptionalUser, require_roles
from app.api.v1.listings import enforce_editor, ensure_viewable, get_property
from app.core.config import get_settings
from app.models.entities import ListingStatus, PropertyPhoto, Role, User
from app.schemas.domain import PhotoOrder, PhotoUpdate, PropertyPhotoResponse
from app.services.media import delete_media, media_path, process_photo, store_photo

router = APIRouter(prefix='/listings/{property_id}/photos', tags=['Listing photos'])
Editor = Annotated[User, Depends(require_roles(Role.owner, Role.admin, Role.broker))]


async def editor_property(property_id: UUID, db: DB, user: Editor):
    property_obj = await get_property(db, property_id, lock=True)
    enforce_editor(user, property_obj)
    return property_obj


async def find_photo(db: DB, property_id: UUID, photo_id: UUID) -> PropertyPhoto:
    photo = await db.scalar(select(PropertyPhoto).where(
        PropertyPhoto.property_id == property_id, PropertyPhoto.id == photo_id,
    ))
    if photo is None:
        raise HTTPException(404, 'Photo not found')
    return photo


@router.post('', response_model=PropertyPhotoResponse, status_code=201)
async def add_photo(
    property_id: UUID, db: DB, user: Editor,
    file: Annotated[UploadFile, File(description='JPEG/PNG/WebP, up to 12 MB')],
    alt_text: Annotated[str, Form(max_length=180)] = '',
    category: Annotated[Literal['gallery', 'floorplan'], Form()] = 'gallery',
):
    await editor_property(property_id, db, user)
    count = await db.scalar(select(func.count(PropertyPhoto.id)).where(PropertyPhoto.property_id == property_id))
    if count >= get_settings().max_property_photos:
        raise HTTPException(409, 'Photo gallery is full (24 images maximum)')
    photo = await process_photo(file)
    main_key, thumb_key = await store_photo(user.tenant_id, property_id, photo)
    try:
        item = PropertyPhoto(
            tenant_id=user.tenant_id, property_id=property_id,
            object_key=main_key, thumbnail_key=thumb_key,
            alt_text=alt_text.strip(), category=category, position=count,
            is_cover=(category == 'gallery' and (await db.scalar(select(func.count(PropertyPhoto.id)).where(
                PropertyPhoto.property_id == property_id, PropertyPhoto.category == 'gallery'))) == 0),
            width=photo.width, height=photo.height, byte_size=len(photo.main),
        )
        db.add(item)
        await db.flush()
        return PropertyPhotoResponse.model_validate(item)
    except Exception:
        await delete_media(main_key, thumb_key)
        raise


@router.get('', response_model=list[PropertyPhotoResponse])
async def get_photos(property_id: UUID, db: DB, user: OptionalUser):
    item = await get_property(db, property_id)
    ensure_viewable(user, item)
    return (await db.scalars(select(PropertyPhoto).where(
        PropertyPhoto.property_id == property_id,
    ).order_by(PropertyPhoto.position, PropertyPhoto.created_at))).all()


@router.get('/{photo_id}/file')
async def photo_file(property_id: UUID, photo_id: UUID, db: DB, user: OptionalUser,
                     variant: Literal['full', 'thumb'] = 'full'):
    item = await get_property(db, property_id)
    ensure_viewable(user, item)
    photo = await find_photo(db, property_id, photo_id)
    location: Path = media_path(photo.thumbnail_key if variant == 'thumb' else photo.object_key)
    if not location.is_file():
        raise HTTPException(404, 'Photo file unavailable')
    cache = 'public, max-age=3600' if item.status == ListingStatus.published else 'private, no-store'
    return FileResponse(location, media_type='image/webp', headers={'Cache-Control': cache,
                        'X-Content-Type-Options': 'nosniff'})


@router.patch('/{photo_id}', response_model=list[PropertyPhotoResponse])
async def update_photo(property_id: UUID, photo_id: UUID, payload: PhotoUpdate, db: DB, user: Editor):
    await editor_property(property_id, db, user)
    photo = await find_photo(db, property_id, photo_id)
    if payload.alt_text is not None:
        photo.alt_text = payload.alt_text.strip()
    if payload.is_cover is True:
        if photo.category != 'gallery':
            raise HTTPException(422, 'A floor plan cannot be the listing cover')
        await db.execute(update(PropertyPhoto).where(PropertyPhoto.property_id == property_id).values(is_cover=False))
        photo.is_cover = True
    await db.flush()
    return (await db.scalars(select(PropertyPhoto).where(
        PropertyPhoto.property_id == property_id,
    ).order_by(PropertyPhoto.position, PropertyPhoto.created_at))).all()


@router.put('/order', response_model=list[PropertyPhotoResponse])
async def reorder_photos(property_id: UUID, payload: PhotoOrder, db: DB, user: Editor):
    await editor_property(property_id, db, user)
    photos = (await db.scalars(select(PropertyPhoto).where(
        PropertyPhoto.property_id == property_id,
    ))).all()
    if len(set(payload.photo_ids)) != len(payload.photo_ids) or set(payload.photo_ids) != {p.id for p in photos}:
        raise HTTPException(422, 'Provide each existing photo exactly once')
    by_id = {p.id: p for p in photos}
    for index, photo_id in enumerate(payload.photo_ids):
        by_id[photo_id].position = index
    await db.flush()
    return [by_id[photo_id] for photo_id in payload.photo_ids]


@router.delete('/{photo_id}', status_code=204)
async def remove_photo(property_id: UUID, photo_id: UUID, db: DB, user: Editor):
    item = await editor_property(property_id, db, user)
    photo = await find_photo(db, property_id, photo_id)
    if item.status == ListingStatus.published:
        total = await db.scalar(select(func.count(PropertyPhoto.id)).where(
            PropertyPhoto.property_id == property_id, PropertyPhoto.category == 'gallery'))
        if photo.category == 'gallery' and total <= 1:
            raise HTTPException(409, 'Unpublish this listing before removing its last photo')
    was_cover = photo.is_cover
    await db.delete(photo)
    await db.flush()
    if was_cover:
        next_photo = await db.scalar(select(PropertyPhoto).where(
            PropertyPhoto.property_id == property_id, PropertyPhoto.category == 'gallery',
        ).order_by(PropertyPhoto.position, PropertyPhoto.created_at))
        if next_photo:
            next_photo.is_cover = True
    # Do not delete files before the transaction commits. A separate media sweep
    # removes unreferenced objects after a safety/grace period.
