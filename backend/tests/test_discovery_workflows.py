"""Integration tests require migrated disposable Postgres/pgvector database."""
from datetime import datetime, timedelta, timezone
from io import BytesIO
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image
from app.main import app


def photo_bytes():
    result = BytesIO()
    Image.new('RGB', (160, 120), (147, 156, 136)).save(result, format='JPEG')
    return result.getvalue()


async def sign_up_agency(client, agency_name):
    slug = f'test-{uuid4().hex[:18]}'
    response = await client.post('/api/v1/auth/tenant/register', json={
        'agency_name': agency_name, 'slug': slug, 'full_name': 'Agency Owner',
        'email': 'agency@example.com', 'password': 'StrongPassWord-123456',
    })
    assert response.status_code == 201, response.text
    return slug, {'Authorization': f"Bearer {response.json()['access_token']}"}


@pytest.mark.asyncio
async def test_saved_search_floorplan_compare_agency_and_visit():
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        slug, agency_headers = await sign_up_agency(client, 'Sample Estate')
        _, another_headers = await sign_up_agency(client, 'Another Estate')
        listing_payload = {
            'title': 'Bright house with separate study', 'kind': 'house', 'purpose': 'sale',
            'city': 'Karachi', 'society': 'DHA', 'block': 'Phase 6', 'area_name': 'Defence',
            'price_negotiable': True, 'ready_to_move': True,
            'price': '30000000', 'area_sqft': '2400', 'bedrooms': 4, 'bathrooms': 4,
            'description': 'A naturally lit house with practical living spaces, a quiet study, outdoor access and secure parking.',
        }
        created = await client.post('/api/v1/listings', headers=agency_headers, json=listing_payload)
        assert created.status_code == 201, created.text
        property_id = created.json()['id']
        floorplan = await client.post(f'/api/v1/listings/{property_id}/photos', headers=agency_headers,
                                      files={'file': ('floorplan.jpg', photo_bytes(), 'image/jpeg')},
                                      data={'category': 'floorplan'})
        assert floorplan.status_code == 201 and floorplan.json()['category'] == 'floorplan'
        assert floorplan.json()['is_cover'] is False
        ready = await client.get(f'/api/v1/listings/{property_id}/readiness', headers=agency_headers)
        assert ready.status_code == 200 and ready.json()['ready'] is False
        gallery = await client.post(f'/api/v1/listings/{property_id}/photos', headers=agency_headers,
                                    files={'file': ('front.jpg', photo_bytes(), 'image/jpeg')},
                                    data={'category': 'gallery'})
        assert gallery.status_code == 201 and gallery.json()['is_cover'] is True
        published = await client.post(f'/api/v1/listings/{property_id}/publish', headers=agency_headers)
        assert published.status_code == 200, published.text

        results = await client.get('/api/v1/listings?society=DHA&block=Phase%206&minimum_bathrooms=3')
        assert results.status_code == 200 and any(p['id'] == property_id for p in results.json()['items'])
        agency = await client.get(f'/api/v1/agencies/{slug}')
        assert agency.status_code == 200 and agency.json()['published_listings'] >= 1
        # Only the owning agency may update its public profile.
        agency_update = await client.patch('/api/v1/agencies/me', headers=agency_headers, json={
            'public_description': 'Family-run property agency in Karachi.', 'public_city': 'Karachi',
            'public_phone': '+923001234567', 'public_email': None,
        })
        assert agency_update.status_code == 200, agency_update.text
        other_search = await client.post('/api/v1/discovery/saved-searches', headers=another_headers,
                                         json={'name': 'Family houses', 'filters': {'city': 'Karachi', 'society': 'DHA'}})
        assert other_search.status_code == 201, other_search.text
        sid = other_search.json()['id']
        matches = await client.get(f'/api/v1/discovery/saved-searches/{sid}/matches', headers=another_headers)
        assert matches.status_code == 200 and any(p['id'] == property_id for p in matches.json()['items'])
        assert (await client.get(f'/api/v1/discovery/saved-searches/{sid}/matches', headers=agency_headers)).status_code == 404
        assert (await client.get('/api/v1/discovery/compare', params={'ids': [property_id, property_id]})).status_code == 422
        visit_time = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        visit = await client.post('/api/v1/viewings', headers=another_headers, json={
            'property_id': property_id, 'preferred_at': visit_time,
            'contact_name': 'Estate Client', 'contact_phone': '+923009999999', 'note': 'Afternoon preferred',
        })
        assert visit.status_code == 201, visit.text
        visit_id = visit.json()['id']
        mine = await client.get('/api/v1/viewings/mine', headers=another_headers)
        assert mine.status_code == 200 and any(v['id'] == visit_id for v in mine.json())
        appointments = await client.get('/api/v1/viewings/agency', headers=agency_headers)
        assert appointments.status_code == 200 and any(v['id'] == visit_id for v in appointments.json())
        forbidden = await client.patch(f'/api/v1/viewings/{visit_id}', headers=another_headers,
                                       json={'status': 'confirmed'})
        assert forbidden.status_code == 403
        confirmed = await client.patch(f'/api/v1/viewings/{visit_id}', headers=agency_headers,
                                       json={'status': 'confirmed'})
        assert confirmed.status_code == 200 and confirmed.json()['status'] == 'confirmed'
        cancelled = await client.patch(f'/api/v1/viewings/{visit_id}', headers=another_headers,
                                       json={'status': 'cancelled'})
        assert cancelled.status_code == 200 and cancelled.json()['status'] == 'cancelled'
