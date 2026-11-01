"""Bounded property-photo processing and filesystem storage.

Only normalized WebP is persisted. Original EXIF/GPS data is discarded.
The storage directory must be a persistent private volume, not a static web root.
"""
import asyncio
import io
import os
import warnings
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import get_settings

Image.MAX_IMAGE_PIXELS = 30_000_000
SUPPORTED_FORMATS = frozenset({'JPEG', 'PNG', 'WEBP'})


@dataclass(frozen=True)
class ProcessedPhoto:
    main: bytes
    thumbnail: bytes
    width: int
    height: int


def _normalized_webp(raw: bytes) -> ProcessedPhoto:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as original:
                if original.format not in SUPPORTED_FORMATS:
                    raise ValueError('Only JPEG, PNG or WebP images are accepted')
                original.load()
                image = ImageOps.exif_transpose(original)
                # JPEG/PNG uploads may contain alpha; flatten onto a neutral backdrop.
                if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
                    rgba = image.convert('RGBA')
                    background = Image.new('RGB', rgba.size, '#f5f3ee')
                    background.paste(rgba, mask=rgba.getchannel('A'))
                    image = background
                else:
                    image = image.convert('RGB')
                image.thumbnail((2600, 2600), Image.Resampling.LANCZOS)
                width, height = image.size
                main = io.BytesIO()
                image.save(main, format='WEBP', quality=84, method=5)
                thumb = image.copy()
                thumb.thumbnail((720, 720), Image.Resampling.LANCZOS)
                thumbnail = io.BytesIO()
                thumb.save(thumbnail, format='WEBP', quality=79, method=5)
                return ProcessedPhoto(main.getvalue(), thumbnail.getvalue(), width, height)
    except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError,
            Image.DecompressionBombWarning) as exc:
        raise HTTPException(422, 'Invalid image. Use a JPEG, PNG or WebP below 30 megapixels.') from exc


async def process_photo(file: UploadFile) -> ProcessedPhoto:
    settings = get_settings()
    maximum = settings.max_photo_upload_mb * 1024 * 1024
    try:
        data = await file.read(maximum + 1)
    finally:
        await file.close()
    if len(data) > maximum:
        raise HTTPException(413, f'Image exceeds {settings.max_photo_upload_mb} MB upload limit')
    if not data:
        raise HTTPException(422, 'Image is empty')
    return await asyncio.to_thread(_normalized_webp, data)


def _target(key: str) -> Path:
    root = Path(get_settings().media_dir).resolve()
    location = (root / key).resolve()
    if not location.is_relative_to(root):
        raise ValueError('Invalid media key')
    return location


def _write_pair(main_key: str, thumb_key: str, photo: ProcessedPhoto) -> None:
    paths = (_target(main_key), _target(thumb_key))
    staged: list[Path] = []
    written: list[Path] = []
    try:
        for path, data in zip(paths, (photo.main, photo.thumbnail)):
            path.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
            temp = path.with_name(path.name + '.tmp-' + uuid4().hex)
            staged.append(temp)
            with temp.open('xb') as stream:
                stream.write(data)
            os.replace(temp, path)
            written.append(path)
    except Exception:
        for path in [*staged, *written]:
            path.unlink(missing_ok=True)
        raise


async def store_photo(tenant_id: UUID, property_id: UUID, photo: ProcessedPhoto) -> tuple[str, str]:
    photo_id = uuid4().hex
    prefix = f'{tenant_id}/{property_id}/{photo_id}'
    main, thumb = f'{prefix}.webp', f'{prefix}-thumb.webp'
    await asyncio.to_thread(_write_pair, main, thumb, photo)
    return main, thumb


def media_path(key: str) -> Path:
    return _target(key)


def _remove_keys(keys: tuple[str, ...]) -> None:
    for key in keys:
        _target(key).unlink(missing_ok=True)


async def delete_media(*keys: str) -> None:
    await asyncio.to_thread(_remove_keys, tuple(keys))
