import os
import pytest
from pydantic import ValidationError
from app.models.entities import PropertyKind
from app.schemas.domain import PGInput, PortionInput, PropertyCreate


def valid_property(**overrides):
    return {'title': 'A bright family apartment', 'kind': 'apartment', 'purpose': 'rent',
            'city': 'Karachi', 'price': '55000', 'area_sqft': '1100', **overrides}


def test_pg_must_be_rental_with_details():
    with pytest.raises(ValidationError):
        PropertyCreate.model_validate(valid_property(kind='pg'))
    with pytest.raises(ValidationError):
        PropertyCreate.model_validate(valid_property(kind='pg', purpose='sale',
                                                    pg={'room_type': 'single', 'total_beds': 1, 'available_beds': 1}))


def test_pg_available_beds_cannot_exceed_total():
    with pytest.raises(ValidationError):
        PGInput(room_type='twin', total_beds=2, available_beds=3)


def test_floor_requires_floor_number():
    with pytest.raises(ValidationError):
        PortionInput(portion_kind='floor')


def test_all_six_property_types_supported():
    assert len(PropertyKind) == 6
    assert PropertyCreate.model_validate(valid_property()).kind == PropertyKind.apartment
