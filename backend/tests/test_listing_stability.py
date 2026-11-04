"""Run with a disposable PostgreSQL database after `alembic upgrade head`."""
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_draft_create_all_kinds_and_form_validation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        slug = f'stability-{uuid4().hex[:12]}'
        signup = await client.post('/api/v1/auth/tenant/register', json={
            'agency_name': 'Stability Test Agency', 'slug': slug,
            'full_name': 'Test Owner', 'email': 'owner@stability.test',
            'password': 'SafePassword-12345',
        })
        assert signup.status_code == 201, signup.text
        headers = {'Authorization': f"Bearer {signup.json()['access_token']}"}
        common = {'title': 'A verified family home', 'description': 'Clean and comfortable property',
                  'city': 'Karachi', 'area_name': 'Clifton', 'price': '4200000',
                  'area_sqft': '1200', 'purpose': 'sale', 'status': 'draft'}
        cases = [
            {'kind': 'house'},
            {'kind': 'apartment'},
            {'kind': 'plot'},
            {'kind': 'commercial_building'},
            {'kind': 'portion', 'portion': {'portion_kind': 'upper'}},
            {'kind': 'pg', 'purpose': 'rent', 'pg': {
                'room_type': 'single', 'total_beds': 1, 'available_beds': 1,
                'food_included': False, 'rules': {},
            }},
        ]
        for case in cases:
            response = await client.post('/api/v1/listings', headers=headers, json={**common, **case})
            assert response.status_code == 201, f'{case["kind"]}: {response.text}'
            item = response.json()
            assert item['kind'] == case['kind']
            assert item['photos'] == []
            assert item['version'] == 1
            assert (item['pg'] is not None) == (case['kind'] == 'pg')
            assert (item['portion'] is not None) == (case['kind'] == 'portion')

        bad = await client.post('/api/v1/listings', headers=headers, json={**common, 'kind': 'house', 'price': '-100'})
        assert bad.status_code == 422, bad.text
        assert bad.json()['error']['code'] == 'VALIDATION_ERROR'
        assert bad.json()['error']['request_id']
        assert bad.headers.get('X-Request-ID')

        forbidden = await client.post('/api/v1/listings', headers=headers,
                                      json={**common, 'kind': 'house', 'status': 'published'})
        assert forbidden.status_code == 422
        assert forbidden.json()['error']['code'] == 'HTTP_422'

        unauthenticated = await client.post('/api/v1/listings', json={**common, 'kind': 'house'})
        assert unauthenticated.status_code == 401
        assert unauthenticated.json()['error']['code'] == 'HTTP_401'
