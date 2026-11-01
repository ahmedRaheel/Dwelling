"""Isolated image security/normalization tests, without a running database."""
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException, UploadFile
from PIL import Image

from app.services import media


def jpeg(size=(1600, 1100)) -> bytes:
    out = BytesIO()
    Image.new('RGB', size, (188, 185, 175)).save(out, format='JPEG')
    return out.getvalue()


@pytest.mark.asyncio
async def test_upload_converts_to_webp_and_generates_thumbnail(tmp_path, monkeypatch):
    monkeypatch.setattr(media, 'get_settings', lambda: SimpleNamespace(
        media_dir=str(tmp_path), max_photo_upload_mb=12,
    ))
    processed = await media.process_photo(UploadFile(filename='home.jpg', file=BytesIO(jpeg())))
    assert processed.width == 1600
    with Image.open(BytesIO(processed.main)) as original:
        assert original.format == 'WEBP'
    with Image.open(BytesIO(processed.thumbnail)) as thumb:
        assert thumb.width <= 720 and thumb.height <= 720
    main_key, thumb_key = await media.store_photo(uuid4(), uuid4(), processed)
    assert media.media_path(main_key).exists()
    assert media.media_path(thumb_key).exists()
    await media.delete_media(main_key, thumb_key)
    assert not media.media_path(main_key).exists()


@pytest.mark.asyncio
async def test_rejects_non_image_and_size_limits(monkeypatch, tmp_path):
    monkeypatch.setattr(media, 'get_settings', lambda: SimpleNamespace(
        media_dir=str(tmp_path), max_photo_upload_mb=1,
    ))
    with pytest.raises(HTTPException) as invalid:
        await media.process_photo(UploadFile(filename='bad.svg', file=BytesIO(b'<svg>not a photo</svg>')))
    assert invalid.value.status_code == 422
    with pytest.raises(HTTPException) as oversized:
        await media.process_photo(UploadFile(filename='huge.jpg', file=BytesIO(b'x' * (1024 * 1024 + 4))))
    assert oversized.value.status_code == 413


def test_media_key_cannot_escape_private_root(tmp_path, monkeypatch):
    monkeypatch.setattr(media, 'get_settings', lambda: SimpleNamespace(media_dir=str(tmp_path)))
    with pytest.raises(ValueError):
        media.media_path('../../etc/passwd')
